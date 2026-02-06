
import sys
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set up path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import Base, get_db
from app.models.meal_plan_history import MealPlanHistory
from app.models.user_profile import UserProfile
from app.services.ai_coach import FitnessCoachService

# Database Setup
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/dbname" # Update if needed, but usually env var
# Actually, let's just use the app's get_db logic? 
# For standalone script, better to reuse config or just mock if we could.
# But we need real DB access for MealPlanHistory.

# Easier: Use the existing main.py app context or just manually connect using env vars if available.
# Let's try to assume the environment is set up or defaults work (localhost:5432)

def verify_history():
    print("--- Starting History Retrieval Verification ---")
    
    # 1. Setup DB Session
    # We'll use the app's database.py setup if possible, assuming env vars are set or defaults work.
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        print("Dataset Connected.")
    except Exception as e:
        print(f"DB Connection Failed: {e}")
        return

    # 2. Find a Test User
    user = db.query(UserProfile).first()
    if not user:
        print("No user profile found to test with.")
        return
    
    print(f"Testing with User ID: {user.id}")
    
    # 3. Create a Dummy History Record for YESTERDAY
    yesterday = datetime.now().date() - timedelta(days=1)
    
    dummy_plan = {
        "breakfast": {"dish": "Test Oatmeal", "calories": 300},
        "lunch": {"dish": "Test Salad", "calories": 400},
        "dinner": {"dish": "Test Chicken", "calories": 500}
    }
    
    # Check if one already exists to avoid clutter
    existing = db.query(MealPlanHistory).filter(
        MealPlanHistory.user_profile_id == user.id,
        MealPlanHistory.created_at >= yesterday,
        MealPlanHistory.created_at < yesterday + timedelta(days=1)
    ).first()
    
    history_record = None
    created_new = False
    
    if existing:
        print(f"Found existing record for {yesterday}")
        history_record = existing
    else:
        print(f"Creating dummy record for {yesterday}")
        history_record = MealPlanHistory(
            user_profile_id=user.id,
            meal_plan_snapshot=dummy_plan,
            created_at=datetime.combine(yesterday, datetime.min.time()) # Set time to start of yesterday
        )
        db.add(history_record)
        db.commit()
        db.refresh(history_record)
        created_new = True

    try:
        # 4. Initialize Service
        coach = FitnessCoachService(db, "test_session_id")
        
        # 5. Test Intent Detection
        print("\n[Test 1] Intent Detection")
        msg = "What was my diet plan yesterday?"
        intent = coach._detect_history_intent(msg)
        print(f"Input: '{msg}'")
        print(f"Result: {intent}")
        
        if intent and intent.get('date') == yesterday:
            print("✅ Intent Detection: SUCCESS")
        else:
            print(f"❌ Intent Detection: FAILED (Expected {yesterday})")

        # 6. Test Data Retrieval
        print("\n[Test 2] Data Retrieval")
        if intent and intent.get('date'):
            data = coach._get_historical_plan(user.id, intent['date'])
            print(f"Retrieved Data: {json.dumps(data, indent=2)}")
            
            if data and (data == dummy_plan or (existing and data == existing.meal_plan_snapshot)):
                 print("✅ Data Retrieval: SUCCESS")
            else:
                 print("❌ Data Retrieval: FAILED")
        else:
            print("Skipping Data Retrieval due to intent failure.")

    finally:
        # 7. Cleanup
        if created_new:
            print("\nCleaning up dummy record...")
            db.delete(history_record)
            db.commit()
        db.close()

if __name__ == "__main__":
    verify_history()
