
from sqlalchemy.orm import Session
from app.models.workout_plan import WorkoutPlan
from app.models.user_profile import UserProfile

"""
Workout Plan CRUD
-----------------
Pure Database Access Object for Workout Plans.
Business logic for generation has been moved to app.services.workout_service.
"""

def get_current_workout_plan(db: Session, user_id: int):
    """
    Retrieve the existing workout plan for a user.
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        return None
    return db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
