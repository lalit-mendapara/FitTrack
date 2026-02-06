from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, SQLALCHEMY_DATABASE_URL
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.workout_preferences import WorkoutPreferences
import sys

# Setup DB connection
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def verify_workout_preferences():
    print("--- Verifying WorkoutPreferences Model ---")
    
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    print("Tables created/verified.")

    # 1. Get an existing user or create a temporary one
    user = db.query(User).filter(User.email == "test_verification@example.com").first()
    if not user:
        print("Creating test user...")
        user = User(email="test_verification@example.com", password="hashed_password", name="Test User")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # 2. Get/Create profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        print("Creating test profile...")
        profile = UserProfile(
            user_id=user.id,
            weight=70, height=175, weight_goal=75,
            fitness_goal="muscle_gain", activity_level="active",
            diet_type="non_veg"
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    # 3. Create WorkoutPreferences
    print("Creating WorkoutPreferences...")
    # constant cleanup for rerunability
    existing_pref = db.query(WorkoutPreferences).filter(WorkoutPreferences.user_profile_id == profile.id).first()
    if existing_pref:
        db.delete(existing_pref)
        db.commit()

    preferences = WorkoutPreferences(
        user_profile_id=profile.id,
        experience_level="beginner",
        days_per_week=4,
        session_duration_min=45,
        health_restrictions="none"
    )
    db.add(preferences)
    db.commit()
    db.refresh(preferences)
    
    print(f"Created Preferences ID: {preferences.id}")

    # 4. Verify Relationship from Profile
    print("Verifying relationship from UserProfile -> WorkoutPreferences...")
    db.refresh(profile)
    if profile.workout_preferences:
        print(f"Success! Profile has preferences: {profile.workout_preferences.experience_level}")
    else:
        print("Error: Profile.workout_preferences is None")
        return False

    # 5. Verify Relationship from Preferences
    print("Verifying relationship from WorkoutPreferences -> UserProfile...")
    if preferences.user_profile:
        print(f"Success! Preferences belongs to profile ID: {preferences.user_profile.id}")
    else:
        print("Error: Preferences.user_profile is None")
        return False

    print("--- Verification Complete ---")
    return True

if __name__ == "__main__":
    try:
        success = verify_workout_preferences()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"Verification failed with error: {e}")
        sys.exit(1)
    finally:
        db.close()
