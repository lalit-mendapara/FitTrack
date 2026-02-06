# app/crud/user_profile.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.user_profile import UserProfile
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate
from datetime import datetime

def get_user_profile(db: Session, user_profile_id: int):
    """Get user profile by its ID"""
    return db.query(UserProfile).filter(UserProfile.id == user_profile_id).first()

def get_user_profile_by_user_id(db: Session, user_id: int):
    """Get user profile by user ID"""
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

def get_user_profile_by_user_and_id(db: Session, user_id: int, profile_id: int):
    """Get specific profile for a user"""
    return db.query(UserProfile).filter(
        and_(
            UserProfile.id == profile_id,
            UserProfile.user_id == user_id
        )
    ).first()

def get_all_user_profiles(db: Session, skip: int = 0, limit: int = 100):
    """Get all user profiles (for admin purposes)"""
    return db.query(UserProfile).offset(skip).limit(limit).all()

def get_user_profiles(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    """Get all profiles for a specific user"""
    return db.query(UserProfile).filter(
        UserProfile.user_id == user_id
    ).offset(skip).limit(limit).all()

def create_user_profile(db: Session, user_profile: UserProfileCreate, user_id: int):
    """
    Create a new user profile - calculations will be handled by SQLAlchemy events
    """
    # Check if user already has a profile
    existing_profile = get_user_profile_by_user_id(db, user_id)
    if existing_profile:
        raise ValueError(f"User {user_id} already has a profile. Use update instead.")
    
    # Create the profile
    db_profile = UserProfile(
        user_id=user_id,
        weight=user_profile.weight,
        height=user_profile.height,
        weight_goal=user_profile.weight_goal,
        fitness_goal=user_profile.fitness_goal,
        activity_level=user_profile.activity_level,
        country=user_profile.country,
        diet_type=user_profile.diet_type or "veg"
        # Note: calories, protein, fat, carbs will be calculated automatically
        # by the SQLAlchemy event listeners in the model
    )
    
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile

def update_user_profile(db: Session, profile_id: int, user_profile_update: UserProfileUpdate):
    """
    Update an existing user profile - calculations will be handled by SQLAlchemy events
    """
    db_profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if not db_profile:
        return None
    
    # Get update data
    update_data = user_profile_update.model_dump(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        if value is not None:
            setattr(db_profile, field, value)
    
    # Note: The before_update event listener will automatically
    # recalculate calories, protein, fat, carbs when needed
    
    db.commit()
    db.refresh(db_profile)
    return db_profile

def update_user_profile_by_user_id(db: Session, user_id: int, user_profile_update: UserProfileUpdate):
    """
    Update user profile by user ID (convenience method)
    """
    db_profile = get_user_profile_by_user_id(db, user_id)
    if not db_profile:
        return None
    
    return update_user_profile(db, db_profile.id, user_profile_update)

def delete_user_profile(db: Session, profile_id: int):
    """Delete a user profile"""
    db_profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
    if db_profile:
        db.delete(db_profile)
        db.commit()
    return db_profile

def delete_user_profile_by_user_id(db: Session, user_id: int):
    """Delete user profile by user ID"""
    db_profile = get_user_profile_by_user_id(db, user_id)
    if db_profile:
        return delete_user_profile(db, db_profile.id)
    return None

def delete_all_user_profiles(db: Session, user_id: int):
    """Delete all profiles for a user (though typically only one exists)"""
    profiles = db.query(UserProfile).filter(UserProfile.user_id == user_id).all()
    for profile in profiles:
        db.delete(profile)
    db.commit()
    return len(profiles)