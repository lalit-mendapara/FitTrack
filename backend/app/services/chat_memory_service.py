from typing import List, Dict, Any
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from config import REDIS_URL

class ChatMemoryService:
    """
    The Notepad: Manages chat history using Redis.
    Stores the last 5 messages with a TTL of 30 minutes.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        # Use a distinct prefix for fitness chat sessions
        self.url = REDIS_URL
        self.history = RedisChatMessageHistory(
            session_id=session_id,
            url=self.url,
            ttl=1800  # 30 minutes
        )
        
        # Dedicated client for metadata (Questions Set)
        # RedisChatMessageHistory might not expose the client reliably
        import redis
        try:
             self.redis_client = redis.from_url(self.url)
        except Exception as e:
             print(f"[ChatMemory] Failed to connect to Redis for metadata: {e}")
             self.redis_client = None

    def add_user_message(self, message: str):
        self.history.add_user_message(message)
        self._trim_history()

    def add_ai_message(self, message: str):
        self.history.add_ai_message(message)
        self._trim_history()

    def get_messages(self) -> List[BaseMessage]:
        return self.history.messages

    def get_last_ai_message(self) -> str:
        """
        Retrieves the content of the last message sent by the AI.
        Returns None if no AI message is found.
        """
        messages = self.get_messages()
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return msg.content
        return None

    def _trim_history(self):
        """
        Ensure only the last 5 messages are kept.
        """
        current_messages = self.history.messages
        if len(current_messages) > 5:
            # Simple approach: since we can't easily pop from complex serialized list without knowing format
            # we rely on the implementation. 
            # If we want to force it, we need to know the key.
            # Langchain Redis History usually uses key `message_store:{session_id}`
            try:
                if self.redis_client:
                    key = f"message_store:{self.session_id}"
                    list_len = self.redis_client.llen(key)
                    if list_len > 5:
                         self.redis_client.lpop(key, list_len - 5)
            except Exception as e:
                print(f"[ChatMemoryService] Warning: Could not trim history: {e}")

    def add_question_to_session(self, question: str):
        """
        Adds a unique question to the session's question list (Newest First).
        """
        try:
            key = f"chat:session:{self.session_id}:questions_v2"
            if self.redis_client:
                # Remove if exists first (to move it to top if repeated)
                self.redis_client.lrem(key, 0, question.strip())
                # Add to top (Left Push)
                self.redis_client.lpush(key, question.strip())
                # Maintain max size (optional, e.g. 50 items)
                self.redis_client.ltrim(key, 0, 49)
                self.redis_client.expire(key, 86400 * 7) 
                print(f"[Memory] Saved question: {question}")
        except Exception as e:
             print(f"[Memory] Failed to save question: {e}")

    def get_session_questions(self) -> List[str]:
        """
        Retrieves all unique questions asked in this session (Ordered Newest First).
        """
        try:
            key = f"chat:session:{self.session_id}:questions_v2"
            if self.redis_client:
                # Get all items
                questions = self.redis_client.lrange(key, 0, -1)
                return [q.decode('utf-8') for q in questions]
            return []
        except Exception as e:
            print(f"[Memory] Failed to get questions: {e}")
            return []

    def clear(self):
        self.history.clear()
        try:
            key = f"chat:session:{self.session_id}:questions_v2"
            if self.redis_client:
                 self.redis_client.delete(key)
        except:
            pass

    def is_empty(self) -> bool:
        """Check if history is empty (needs hydration)."""
        try:
            return len(self.history.messages) == 0
        except:
            return True

    def hydrate_messages(self, messages: List[BaseMessage]):
        """Populate Redis history from DB list."""
        self.history.clear() # Ensure clean state
        for msg in messages:
            if msg.type == "human":
                self.history.add_user_message(msg.content)
            elif msg.type == "ai":
                self.history.add_ai_message(msg.content)
                
    def hydrate_questions(self, questions: List[str]):
        """Populate Questions List from DB list."""
        try:
            key = f"chat:session:{self.session_id}:questions_v2"
            if self.redis_client and questions:
                # We need to add them such that the newest is at index 0.
                # If `questions` list passed here is ordered [Newest, ..., Oldest],
                # we should push them in REVERSE order so Newest ends up at head.
                # OR, if we use rpush (Right Push), we build the list [Newest, ..., Oldest].
                # Let's assume input `questions` is [Newest, ..., Oldest] (coming from DB desc order).
                
                # Delete existing key to start fresh
                self.redis_client.delete(key)
                
                # Use RPUSH to preserve the order of the input list in the Redis list
                # If input is [Q1_newest, Q2, Q3_oldest]
                # RPUSH -> [Q1_newest, Q2, Q3_oldest]
                # LRANGE 0 -1 -> [Q1_newest, Q2, Q3_oldest] -> Correct.
                self.redis_client.rpush(key, *questions)
                self.redis_client.expire(key, 86400 * 7)
        except Exception as e:
            print(f"[Memory] Failed to hydrate questions: {e}")
