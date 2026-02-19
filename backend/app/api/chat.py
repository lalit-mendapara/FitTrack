from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.services.ai_coach import FitnessCoachService
from app.api.auth import get_current_user
from app.models.chat import ChatHistory, ChatSession
from app.services.llm_service import generate_chat_title, generate_refined_chat_title, LANGFUSE_ENABLED
from app.services.chat_memory_service import ChatMemoryService
from datetime import datetime
import sys

# Langfuse tracing - creates root trace for chat requests
observe = lambda *args, **kwargs: (lambda f: f)  # No-op decorator fallback
if sys.version_info < (3, 14):
    try:
        from langfuse import observe
    except ImportError:
        pass

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    source: str
    session_id: str
    title: Optional[str] = None

class SessionSchema(BaseModel):
    session_id: str
    title: str
    last_active: datetime

@router.post("/chat", response_model=ChatResponse)
@observe(name="chat_with_coach")
async def chat_with_coach(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Interact with the Fitness Coach. 
    Creates a new session if it doesn't exist.
    Auto-generates title for new sessions.
    """
    user_id = current_user.id
    session_id = request.session_id
    
    # 1. Manage Session
    # Check if session exists globally to prevent UniqueViolation
    chat_session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    
    is_new_session = False
    
    if chat_session:
        # Verify ownership
        if chat_session.user_id != user_id:
            print(f"[Chat API] Security Alert: User {user_id} tried to access Session {session_id} belonging to User {chat_session.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This session ID belongs to another user. Please start a new chat."
            )
    else:
        # Create new session
        is_new_session = True
        chat_session = ChatSession(
            user_id=user_id,
            session_id=session_id,
            title="New Chat"
        )
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        print(f"[Chat API] Created new session: {session_id}")
    
    # Auto-generate title if it's "New Chat" or newly created
    should_generate_title = is_new_session or chat_session.title == "New Chat"

    # 2. Process Message
    # Prefix session with user_id for Redis scoping if needed 
    # (FitnessCoachService uses session_id for Redis key, usually we want unique global or per user)
    # The existing code did: session_key = f"user_{user_id}_{request.session_id}"
    session_key = f"user_{user_id}_{session_id}"
    
    try:
        coach = FitnessCoachService(db, session_id=session_key)
        # Updated signature: user_message, user_id, session_id
        response_data = await coach.get_response(request.message, user_id, session_key)
        
        # 3. Save History
        db.add(ChatHistory(
            user_id=user_id,
            role="user",
            content=request.message,
            session_id=session_id
        ))
        db.add(ChatHistory(
            user_id=user_id,
            role="assistant",
            content=response_data["content"],
            custom_content=response_data.get("custom_content"),
            session_id=session_id
        ))
        
        # Update session timestamp
        chat_session.updated_at = datetime.utcnow()
        
        db.commit()
        
        # 4. Generate Title in Background (Dynamic Refinement)
        # Generate title based on content analysis with progressive refinement
        message_count = db.query(ChatHistory).filter(ChatHistory.session_id == session_id).count()
        
        trigger_mode = None
        if message_count <= 3 and (is_new_session or chat_session.title == "New Chat"):
            # Initial title generation for new sessions
            trigger_mode = "initial"
        elif 4 <= message_count <= 5:
            # Progressive refinement for questions 4-5
            trigger_mode = "progressive"
        elif message_count == 6:
            # Final comprehensive summary after 6 questions
            trigger_mode = "comprehensive"
            
        if trigger_mode:
            print(f"[Chat API] Triggering '{trigger_mode}' title generation for {session_id}")
            background_tasks.add_task(update_session_title, session_id, user_id, request.message, trigger_mode)
        
        return ChatResponse(
            response=response_data["content"], 
            source=response_data["source"],
            session_id=session_id,
            title=chat_session.title 
        )
        
    except Exception as e:
        print(f"[Chat API] Error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The coach is currently unavailable."
        )

def update_session_title(session_id: str, user_id: int, first_message: str, trigger_mode: str = "initial"):
    """Background task to generate and save chat title"""
    try:
        from app.database import SessionLocal
        
        with SessionLocal() as db_session:
             session = db_session.query(ChatSession).filter(
                 ChatSession.session_id == session_id,
                 ChatSession.user_id == user_id
             ).first()
             
             if not session:
                 print(f"[Chat API] Session {session_id} not found during title update.")
                 return

             title = "New Chat"
             
             if trigger_mode == "initial":
                 # Fast, simple generation based on first message
                 from app.services.llm_service import generate_chat_title
                 title = generate_chat_title(first_message)
             
             elif trigger_mode == "progressive":
                 # Progressive refinement for questions 4-5 - focus on latest content
                 from app.services.llm_service import generate_refined_chat_title
                 latest_msgs = db_session.query(ChatHistory).filter(ChatHistory.session_id == session_id).order_by(ChatHistory.id.desc()).limit(3).all()
                 history = [{"role": m.role, "content": m.content} for m in latest_msgs[::-1]]  # Reverse for chronological
                 title = generate_refined_chat_title(history)
             
             elif trigger_mode == "comprehensive":
                 # Comprehensive summary after 6 questions - analyze full conversation
                 from app.services.llm_service import generate_comprehensive_chat_title
                 all_msgs = db_session.query(ChatHistory).filter(ChatHistory.session_id == session_id).order_by(ChatHistory.id.asc()).all()
                 history = [{"role": m.role, "content": m.content} for m in all_msgs]
                 title = generate_comprehensive_chat_title(history)

             # Update title
             session.title = title
             db_session.commit()
             print(f"[Chat API] Updated Title ({trigger_mode}) for {session_id}: {title}")
                 
    except Exception as e:
        print(f"[Chat API] Title Generation Error: {e}")

@router.get("/chat/history")
def get_chat_history(
    session_id: Optional[str] = "default_session",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch API history for a specific session.
    """
    # Verify session belongs to user (optional but good security)
    # Just filtering by user_id in ChatHistory is sufficient for data safety.
    
    history = db.query(ChatHistory).filter(
        ChatHistory.user_id == current_user.id,
        ChatHistory.session_id == session_id
    ).order_by(ChatHistory.id.desc()).limit(50).all()
    
    return [{"id": msg.id, "role": msg.role, "content": msg.content, "custom_content": msg.custom_content, "timestamp": msg.created_at} for msg in reversed(history)]

class AddHistoryRequest(BaseModel):
    session_id: str
    role: str # user, assistant
    content: str
    custom_content: Optional[dict] = None
    
@router.post("/chat/history")
def add_chat_history(
    request: AddHistoryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Manually add a message to the chat history (e.g. for system events/scripts).
    """
    # Verify session exists and belongs to user
    session = db.query(ChatSession).filter(
        ChatSession.session_id == request.session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    # Auto-create session if it doesn't exist (fixing 404 for client-side triggered events)
    if not session:
        session = ChatSession(
            user_id=current_user.id,
            session_id=request.session_id,
            title="New Chat"
        )
        db.add(session)
        db.commit() # Commit to get ID/persist
        db.refresh(session)
        
    history = ChatHistory(
        user_id=current_user.id,
        session_id=request.session_id,
        role=request.role,
        content=request.content,
        custom_content=request.custom_content
    )
    db.add(history)
    session.updated_at = datetime.utcnow()
    db.commit()
    
    db.commit()
    
    # Trigger Title Generation for new sessions
    # Check if we should generate title
    message_count = db.query(ChatHistory).filter(ChatHistory.session_id == request.session_id).count()
    if session.title == "New Chat" and message_count <= 5:
        # Use content as context
        background_tasks.add_task(update_session_title, request.session_id, current_user.id, request.content, "initial")

    return {"message": "History added"}

@router.get("/chat/sessions", response_model=List[SessionSchema])
def get_chat_sessions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of chat sessions for the user.
    """
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(desc(ChatSession.updated_at), desc(ChatSession.id)).all()
    
    return [
        {
            "session_id": s.session_id, 
            "title": s.title, 
            "last_active": s.updated_at
        } 
        for s in sessions
    ]

class RenameSessionRequest(BaseModel):
    title: str

@router.delete("/chat/sessions/{session_id}")
def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a chat session and all its history.
    """
    # Find the session
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Delete all chat history for this session
    db.query(ChatHistory).filter(
        ChatHistory.session_id == session_id,
        ChatHistory.user_id == current_user.id
    ).delete()
    
    # Delete the session
    db.delete(session)
    db.commit()
    
    # Also clear Redis memory if exists
    try:
        session_key = f"user_{current_user.id}_{session_id}"
        memory = ChatMemoryService(session_key)
        memory.clear()
        print(f"[Chat API] Deleted session and cleared Redis: {session_id}")
    except Exception as e:
        print(f"[Chat API] Warning: Could not clear Redis for {session_id}: {e}")
    
    return {"message": "Session deleted successfully", "session_id": session_id}

@router.patch("/chat/sessions/{session_id}")
def rename_chat_session(
    session_id: str,
    request: RenameSessionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Rename a chat session title.
    """
    # Find the session
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Update title
    new_title = request.title.strip()
    if not new_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title cannot be empty"
        )
    
    session.title = new_title
    session.updated_at = datetime.utcnow()
    db.commit()
    
    print(f"[Chat API] Renamed session {session_id} to: {new_title}")
    
    return {"message": "Session renamed successfully", "session_id": session_id, "title": new_title}

@router.get("/chat/debug-context/{session_id}")
def debug_chat_context(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Debug: View raw Redis memory for a session (Messages + Questions).
    """
    session_key = f"user_{current_user.id}_{session_id}"
    memory = ChatMemoryService(session_key)
    
    # Get Messages
    raw_messages = memory.get_messages()
    formatted_messages = [
        {"role": m.type, "content": m.content} 
        for m in raw_messages
    ]
    
    # Get Questions
    questions = memory.get_session_questions()
    
    return {
        "session_id": session_id,
        "redis_key": session_key,
        "message_count": len(formatted_messages),
        "question_count": len(questions),
        "messages": formatted_messages,
        "questions_list": questions
    }

class UpdateHistoryRequest(BaseModel):
    custom_content: Optional[dict] = None

@router.patch("/chat/history/{message_id}")
def update_chat_history_item(
    message_id: int,
    request: UpdateHistoryRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update the custom_content of a specific chat message.
    Used for persisting UI states like 'isStatic'.
    """
    history_item = db.query(ChatHistory).filter(
        ChatHistory.id == message_id,
        ChatHistory.user_id == current_user.id
    ).first()
    
    if not history_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
        
    history_item.custom_content = request.custom_content
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(history_item, "custom_content")
    
    db.commit()
    
    return {"message": "History updated", "id": message_id}

@router.delete("/chat/history/{message_id}")
def delete_chat_history_item(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a specific chat message.
    """
    history_item = db.query(ChatHistory).filter(
        ChatHistory.id == message_id,
        ChatHistory.user_id == current_user.id
    ).first()
    
    if not history_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
        
    db.delete(history_item)
    db.commit()
    
    return {"message": "Message deleted", "id": message_id}
