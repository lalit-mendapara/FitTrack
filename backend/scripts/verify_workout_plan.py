from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, SQLALCHEMY_DATABASE_URL
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.workout_plan import WorkoutPlan
import sys
import json

# Setup DB connection
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def verify_workout_plan():
    print("--- Verifying WorkoutPlan Model ---")
    
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    print("Tables created/verified.")

    # 1. Get User/Profile (Using known ID from previous verifying step if possible, or query)
    profile = db.query(UserProfile).first()
    if not profile:
        print("Error: No user profile found. Run workout_preferences verification first.")
        return False
    
    print(f"Using Profile ID: {profile.id}")

    # 2. Mock Data
    mock_data = {
      "plan_name": "4-Day Upper/Lower Split for Hypertrophy",
      "duration_weeks": 8,
      "primary_goal": "muscle_gain",
      "weekly_schedule": {
        "day1": {
          "day_name": "Upper Body Strength",
          "focus": "chest, back, shoulders",
          "exercises": [
            {
              "exercise": "Barbell Bench Press",
              "sets": 4,
              "reps": "6-8",
              "rest_sec": 120,
              "image_url": "https://fitnessprogramer.com/wp-content/uploads/2021/02/Barbell-Bench-Press.gif"
            }
          ],
          "cardio": "none",
          "session_duration_min": 60
        }
      },
      "progression_guidelines": ["Increase weight by 2.5kg", "Deload every 4th week"],
      "cardio_recommendations": ["10k steps daily"]
    }

    # 3. Create WorkoutPlan
    print("Creating WorkoutPlan...")
    
    # Cleanup old plan
    existing_plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
    if existing_plan:
        db.delete(existing_plan)
        db.commit()

    plan = WorkoutPlan(
        user_profile_id=profile.id,
        plan_name=mock_data["plan_name"],
        duration_weeks=mock_data["duration_weeks"],
        primary_goal=mock_data["primary_goal"],
        weekly_schedule=mock_data["weekly_schedule"],
        progression_guidelines=mock_data["progression_guidelines"],
        cardio_recommendations=mock_data["cardio_recommendations"]
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    print(f"Created Plan ID: {plan.id}")

    # 4. Verify Fetch and JSONB
    print("Verifying JSONB data retrieval...")
    fetched_plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan.id).first()
    
    if fetched_plan.weekly_schedule['day1']['day_name'] == "Upper Body Strength":
        print("Success! Nested JSON data retrieved correctly.")
        # Verify image_url
        exercises = fetched_plan.weekly_schedule['day1']['exercises']
        if exercises and 'image_url' in exercises[0]:
             print(f"Success! image_url found: {exercises[0]['image_url']}")
        else:
             print("Error: image_url missing in fetched data.")
    else:
        print("Error: JSON data mismatch.")
        print(fetched_plan.weekly_schedule)
        return False
        
    if len(fetched_plan.progression_guidelines) == 2:
         print("Success! Array JSON data retrieved correctly.")
    else:
         print("Error: Array JSON data mismatch.")
         return False

    print("--- Verification Complete ---")
    return True

if __name__ == "__main__":
    try:
        success = verify_workout_plan()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"Verification failed with error: {e}")
        sys.exit(1)
    finally:
        db.close()
