import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai_coach import FitnessCoachService
from config import SQLALCHEMY_DATABASE_URL

def test_coach():
    print("\n--- Testing FitnessCoachService (The Brain) ---")
    
    if not SQLALCHEMY_DATABASE_URL:
        print("Error: SQLALCHEMY_DATABASE_URL not set.")
        return

    # Setup DB
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    # User ID 1 is usually the default test user
    user_id = 1 
    session_id = "test_coach_session_v1"
    
    try:
        coach = FitnessCoachService(db, session_id)
        
        # 1. Test Librarian Mode
        print("\n[Query 1] Librarian Mode: 'What creates more muscle, chicken or tofu?'")
        response1 = coach.get_response(user_id, "What creates more muscle, chicken or tofu?")
        print(f"Coach Says: {response1[:200]}...") # Print first 200 chars

        # 2. Test Auditor Mode
        print("\n[Query 2] Auditor Mode: 'What should I eat for lunch today?'")
        response2 = coach.get_response(user_id, "What should I eat for lunch today?")
        print(f"Coach Says: {response2[:200]}...")

        # 3. Test Strategist Mode
        print("\n[Query 3] Strategist Mode: 'I want to lose weight, tell me a strategy based on my stats.'")
        response3 = coach.get_response(user_id, "I want to lose weight, tell me a strategy based on my stats.")
        print(f"Coach Says: {response3[:200]}...")
        
    except Exception as e:
        print(f"Coach Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_coach()
