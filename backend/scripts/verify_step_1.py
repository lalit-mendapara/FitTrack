import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_service import VectorService
from app.services.chat_memory_service import ChatMemoryService
from app.services.stats_service import StatsService
from config import SQLALCHEMY_DATABASE_URL

def test_vector_service():
    print("\n--- Testing VectorService (The Librarian) ---")
    try:
        service = VectorService()
        if service.client:
            print("Qdrant Initialized.")
            # Only run search if not a dummy test
            # results = service.search_food("chicken")
            # print(f"Search Results: {len(results)}")
        else:
            print("Qdrant Client not initialized (Env vars missing or connection failed).")
    except Exception as e:
        print(f"VectorService Error: {e}")

def test_chat_memory():
    print("\n--- Testing ChatMemoryService (The Notepad) ---")
    try:
        service = ChatMemoryService(session_id="test_session_123")
        service.add_user_message("Hello")
        service.add_ai_message("Hi there")
        
        msgs = service.get_messages()
        print(f"Messages in history: {len(msgs)}")
        print("Latest:", msgs[-1].content if msgs else "None")
        
        # Cleanup
        service.clear()
        print("Memory cleared.")
    except Exception as e:
        print(f"ChatMemoryService Error (Redis reachable?): {e}")

def test_stats_service():
    print("\n--- Testing StatsService (The Auditor) ---")
    if not SQLALCHEMY_DATABASE_URL:
        print("No DATABASE_URL found.")
        return

    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        service = StatsService(db)
        # Try capturing a profile if users exist, else valid but empty
        # We assume user_id 1 might exist or just check method validity
        try:
            profile = service.get_user_profile(user_id=1) 
            print(f"Fetched Profile for User 1: {'Found' if profile else 'Not Found'}")
            
            plan = service.get_todays_plan(user_id=1)
            print(f"Fetched Today's Plan: {plan['day']}")
        except Exception as inner_e:
             print(f"Database Query Error: {inner_e}")
             
        db.close()
    except Exception as e:
        print(f"StatsService Error: {e}")

if __name__ == "__main__":
    test_vector_service()
    test_chat_memory()
    test_stats_service()
