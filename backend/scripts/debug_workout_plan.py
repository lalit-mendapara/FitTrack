import sys
import os
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.crud.workout_plan import generate_workout_plan_for_user
from app.schemas.workout_plan import WorkoutPlanRequestData, WorkoutPreferencesInput

def debug_generation():
    db = SessionLocal()
    try:
        # User ID 12 as per user request
        user_id = 12
        
        print(f"Testing for User ID: {user_id}")
        
        prefs = WorkoutPreferencesInput(
            experience_level="beginner",
            days_per_week=4,
            session_duration_min=45,
            health_restrictions="none"
        )
        
        request_data = WorkoutPlanRequestData(
            user_id=user_id,
            workout_preferences=prefs
        )
        
        print("Calling generate_workout_plan_for_user...")
        plan = generate_workout_plan_for_user(db, request_data)
        
        if plan:
            print("✅ Plan generated successfully!")
            print(str(plan)[:200] + "...")
        else:
            print("❌ Plan generation returned None.")
            
    except Exception as e:
        print(f"❌ Exception caught in test script: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_generation()
