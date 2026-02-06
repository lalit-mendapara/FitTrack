from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.workout_preferences import WorkoutPreferencesCreate, WorkoutPreferencesUpdate, WorkoutPreferencesResponse
from app.crud import workout_preferences as crud_workout_preferences
from app.api.auth import get_current_user

router = APIRouter(
    prefix="/workout-preferences",
    tags=["workout-preferences"]
)

@router.get("/me", response_model=WorkoutPreferencesResponse)
def get_my_workout_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # First get user profile
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Please complete physical profile first."
        )
    
    workout_preferences = crud_workout_preferences.get_by_user_profile_id(db, user_profile_id=user_profile.id)
    if not workout_preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout preferences not found"
        )
    return workout_preferences

@router.post("/", response_model=WorkoutPreferencesResponse)
def create_or_update_workout_preferences(
    preferences_in: WorkoutPreferencesCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # First get user profile
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Please complete physical profile first."
        )
    
    # Check if preferences already exist
    existing_preferences = crud_workout_preferences.get_by_user_profile_id(db, user_profile_id=user_profile.id)
    
    if existing_preferences:
        # Update
        update_schema = WorkoutPreferencesUpdate(**preferences_in.model_dump())
        return crud_workout_preferences.update(db, db_obj=existing_preferences, obj_in=update_schema)
    else:
        # Create
        return crud_workout_preferences.create(db, obj_in=preferences_in, user_profile_id=user_profile.id)
