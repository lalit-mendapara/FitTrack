
import sys
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.database import Base, get_db
from app.models.meal_plan_history import MealPlanHistory
from app.models.user_profile import UserProfile
from app.services.ai_coach import FitnessCoachService

def verify_context_filtering():
    print("--- Starting Context Filtering Verification ---")
    
    # 1. Mock Data Setup (Minimal)
    mock_context = {
        "profile": {"name": "TestUser"},
        "meal_plan": [{"meal": "lunch", "dish": "Salad"}],
        "workout_plan": {
            "schedule": {
                "Monday": {"focus": "Chest", "exercises": [{"exercise": "Pushups"}]}
            }
        }
    }
    
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        coach = FitnessCoachService(db, "test_filter_session")
        
        # Test 1: Diet Only Scope
        print("\nTest 1: Diet Scope (Expect: No Workout Schedule)")
        prompt_diet = coach._build_system_prompt(
            mock_context, [], [], [], 
            include_diet=True, 
            include_workout=False
        )
        
        if "weekly workout schedule" not in prompt_diet.lower():
            print("✅ SUCCESS: Workout Schedule excluded from Diet-Only prompt.")
        else:
            print("❌ FAILED: Workout Schedule matched in Diet-Only prompt.")
            
        # Test 2: Workout Only Scope
        print("\nTest 2: Workout Scope (Expect: No Diet Plan)")
        prompt_workout = coach._build_system_prompt(
            mock_context, [], [], [], 
            include_diet=False, 
            include_workout=True
        )
        
        if "daily diet" not in prompt_workout.lower() and "scheduled" not in prompt_workout.lower():
             print("✅ SUCCESS: Diet Plan excluded from Workout-Only prompt.")
        else:
             print("❌ FAILED: Diet Plan matched in Workout-Only prompt.")
             
        # Test 3: Default (Both)
        print("\nTest 3: General Scope (Expect: Both)")
        prompt_general = coach._build_system_prompt(
             mock_context, [], [], []
        ) # Defaults True
        
        if "weekly workout schedule" in prompt_general.lower() and "daily diet" in prompt_general.lower():
             print("✅ SUCCESS: Both included in General prompt.")
        else:
             print("❌ FAILED: Missing sections in General prompt.")

    except Exception as e:
        print(f"Test Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_context_filtering()
