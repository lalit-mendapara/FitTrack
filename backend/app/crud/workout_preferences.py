from sqlalchemy.orm import Session
from app.models.workout_preferences import WorkoutPreferences
from app.schemas.workout_preferences import WorkoutPreferencesCreate, WorkoutPreferencesUpdate

def get_by_user_profile_id(db: Session, user_profile_id: int):
    return db.query(WorkoutPreferences).filter(WorkoutPreferences.user_profile_id == user_profile_id).first()

def create(db: Session, obj_in: WorkoutPreferencesCreate, user_profile_id: int):
    db_obj = WorkoutPreferences(
        **obj_in.model_dump(),
        user_profile_id=user_profile_id
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update(db: Session, db_obj: WorkoutPreferences, obj_in: WorkoutPreferencesUpdate):
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
