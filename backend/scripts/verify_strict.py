
import sys
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import Base, get_db
from app.models.meal_plan_history import MealPlanHistory
from app.models.tracking import FoodLog
from app.models.user_profile import UserProfile
from app.services.ai_coach import FitnessCoachService

def verify_strict_matching():
    print("--- Starting Strict Matching Verification ---")
    
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        print("Dataset Connected.")
    except Exception as e:
        print(f"DB Connection Failed: {e}")
        return

    user = db.query(UserProfile).first()
    if not user:
        print("No user profile found.")
        return
    
    print(f"Testing with User ID: {user.user_id}")
    
    yesterday_date = datetime.now().date() - timedelta(days=1)
    
    # Setup: 2 Plans
    # Plan A: "Cheese Slice" (Snack)
    # Plan B: "Roasted Peanuts" (Snack)
    # Log: "Roasted Peanuts"
    
    plan_a_time = datetime.combine(yesterday_date, datetime.min.time()) + timedelta(hours=8)
    plan_a = MealPlanHistory(
        user_profile_id=user.id,
        meal_plan_snapshot={
            "breakfast": {"dish": "Oatmeal"},
            "snack": {"dish": "Cheese Slice"}
        },
        created_at=plan_a_time
    )
    
    plan_b_time = datetime.combine(yesterday_date, datetime.min.time()) + timedelta(hours=9)
    plan_b = MealPlanHistory(
        user_profile_id=user.id,
        meal_plan_snapshot={
            "breakfast": {"dish": "Oatmeal"},
            "snack": {"dish": "Roasted Peanuts"}
        },
        created_at=plan_b_time
    )
    
    log_entry = FoodLog(
        user_id=user.user_id,
        date=yesterday_date,
        food_name="Roasted Peanuts", # EXACT MATCH for Plan B
        calories=150
    )
    
    db.add(plan_a)
    db.add(plan_b)
    db.add(log_entry)
    db.commit()
    print(f"Created Plans & Log for {yesterday_date}")

    try:
        coach = FitnessCoachService(db, "test_strict_session")
        
        # Test Data Retrieval
        # We expect Plan B to be picked because "Roasted Peanuts" is an exact match (Score 10)
        # Plan A has NO match for "Roasted Peanuts" (Score 0)
        
        result = coach._get_historical_plan(user.user_id, yesterday_date)
        
        if result:
            snapshot = result['full_plan']
            snack_dish = snapshot.get('snack', {}).get('dish')
            
            print(f"Selected Plan Snack: {snack_dish}")
            
            if snack_dish == "Roasted Peanuts":
                 print("✅ SUCCESS: System selected Plan B (Exact Match)")
            else:
                 print(f"❌ FAILED: System selected {snack_dish} (Expected Roasted Peanuts)")
            
        else:
            print("❌ Error: No result returned.")

    finally:
        print("\nCleaning up test data...")
        db.delete(plan_a)
        db.delete(plan_b)
        db.delete(log_entry)
        db.commit()
        db.close()

if __name__ == "__main__":
    verify_strict_matching()
