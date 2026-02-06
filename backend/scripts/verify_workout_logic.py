
import sys
import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import SQLALCHEMY_DATABASE_URL
from app.database import Base, get_db
from app.services.workout_service import generate_workout_plan
from app.schemas.workout_plan import WorkoutPlanRequestData, WorkoutPreferencesInput

# Mock Request Data
# Assuming user_id 1 exists. If not, this script might fail or need adjustment.
user_id = 1 

# Mock Data
request_data = WorkoutPlanRequestData(
    user_id=user_id,
    workout_preferences=WorkoutPreferencesInput(
        experience_level="Intermediate",
        days_per_week=4, # Should generate a split
        session_duration_min=60,
        health_restrictions="None"
    ),
    custom_prompt="Focus on building muscle. Ensure 4 exercises per muscle group logic is followed."
)

from app.models.user_profile import UserProfile

# ...

def verify_logic():
    print("Connecting to DB...")
    # SQLALCHEMY_DATABASE_URL imported from config
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Get first available user profile
        profile = db.query(UserProfile).first()
        if not profile:
            print("Error: No UserProfile found in database. Cannot run verification.")
            return
            
        user_id = profile.user_id
        print(f"Using found UserProfile ID: {profile.id} (User ID: {user_id})")

        # Update request data with real user_id
        request_data.user_id = user_id
        
        print(f"Generating workout plan for user {user_id}...")
        result = generate_workout_plan(db, request_data)
        
        plan = result["workout_plan"]
        schedule = plan.get("weekly_schedule", {})
        
        print(f"\nPlan Generated: {plan.get('plan_name')}")
        
        for day, details in schedule.items():
            print(f"\nDay: {details.get('day_name')}")
            muscle_group = details.get("primary_muscle_group", "Unknown")
            print(f"Target: {muscle_group}")
            
            exercises = details.get("exercises", [])
            print(f"Total Exercises: {len(exercises)}")
            
            for i, ex in enumerate(exercises):
                print(f"  {i+1}. {ex['exercise']} (Target: {ex.get('target_muscle', 'N/A')})")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_logic()
