from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, SQLALCHEMY_DATABASE_URL
from app.models.exercise import Exercise
import sys

# Setup DB connection
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def verify_exercise_model():
    print("--- Verifying Exercise Model ---")
    
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    print("Tables created/verified.")

    # Create an exercise
    print("Creating test exercise...")
    exercise = Exercise(
        name="Deadlift",
        category="Strength",
        primary_muscle="Back",
        difficulty="Advanced",
        image_url="https://example.com/deadlift.gif"
    )
    
    # Check if duplicate exists for this test run (optional, but good for idempotency)
    existing = db.query(Exercise).filter(Exercise.name == "Deadlift").first()
    if existing:
        db.delete(existing)
        db.commit()

    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    
    print(f"Created Exercise ID: {exercise.id}, Name: {exercise.name}")

    # Read it back
    fetched = db.query(Exercise).filter(Exercise.id == exercise.id).first()
    if fetched and fetched.name == "Deadlift":
        print("Success! Exercise fetched correctly.")
    else:
        print("Error: Could not fetch exercise.")
        return False

    print("--- Verification Complete ---")
    return True

if __name__ == "__main__":
    try:
        success = verify_exercise_model()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"Verification failed with error: {e}")
        sys.exit(1)
    finally:
        db.close()
