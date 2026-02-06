import sys
import os
import time

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.services.ai_coach import FitnessCoachService
from sqlalchemy import text

def test_librarian():
    db = SessionLocal()
    # Use a dummy session ID
    coach = FitnessCoachService(db, session_id="test_librarian_v1")
    
    test_cases = [
        {
            "name": "1. Exact Match (Food)",
            "query": "How many calories in 100g of Poha?",
            "expected_source": "Library"
        },
        {
            "name": "2. Instructional (Exercise)",
            "query": "How do I perform a Barbell Bench Press correctly?",
            "expected_source": "Library"
        },
        {
            "name": "3. Hybrid Fallback (Missing Item)",
            "query": "What is the protein in Dragonfruit?",
            "expected_source": "General AI"
        },
        {
            "name": "4. Multi-Query (Comparison)",
            "query": "Compare the protein in eggs vs chicken breast.",
            "expected_source": "Library"
        }
    ]

    print("--- 🧠 LIBRARIAN ANGLE VERIFICATION ---")
    
    # Fetch valid user ID
    user_stmt = "SELECT id FROM users LIMIT 1"
    valid_user_id = db.execute(text(user_stmt)).scalar() or 1
    print(f"Using User ID: {valid_user_id}")

    for test in test_cases:
        print(f"\n[TEST] {test['name']}")
        print(f"Query: '{test['query']}'")
        
        start = time.time()
        # Ensure we suppress FK errors for chat history in this test script or use valid ID
        try:
            result = coach.get_response(valid_user_id, test['query'])
        except Exception as e:
            print(f"Error calling coach: {e}")
            continue

        duration = time.time() - start
        
        # Check format (Dict or Str?)
        if isinstance(result, dict):
            content = result["content"]
            source = result["source"]
        else:
            content = result
            source = "Unknown"

        print(f"Source: {source} (Expected: {test['expected_source']})")
        print(f"Time: {duration:.2f}s")
        print(f"Response Snippet: {content[:150]}...")
        
        # Basic Assertions
        if source == test['expected_source']:
            print("✅ SOURCE CHECK PASS")
        else:
            print("❌ SOURCE CHECK FAIL")

        # Specific Content Checks
        if "Dragonfruit" in test['name']:
            if "not in our library" in content:
                print("✅ DISCLAIMER CHECK PASS")
            else:
                print("❌ DISCLAIMER CHECK FAIL")
                
        if "Instructional" in test['name']:
            if "1." in content and "2." in content:
                 print("✅ NUMBERED STEPS CHECK PASS")
            else:
                 print("⚠️ STEPS CHECK WARNING (Check manually)")

    db.close()

if __name__ == "__main__":
    test_librarian()
