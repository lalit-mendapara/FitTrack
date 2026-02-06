# app/api/routes/user_profile.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.user_profile import UserProfileCreate, UserProfileResponse, UserProfileUpdate, UserProfileRequest
from pydantic import BaseModel
from app.crud import user_profile as crud_user_profile
from app.crud import user as crud_user
from app.models.user import User
from app.api.auth import get_current_user


router = APIRouter(prefix="/user-profiles", tags=["user-profiles"])

# POST - Create new user profile for current user
@router.post("/", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
def create_user_profile(
    profile: UserProfileCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new user profile for the authenticated user.
    """
    # Check if user already has a profile
    existing_profile = crud_user_profile.get_user_profile_by_user_id(db, user_id=current_user.id)
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User already has a profile. Use PUT to update."
        )
    
    try:
        new_profile = crud_user_profile.create_user_profile(db, profile, current_user.id)
        
        return new_profile
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )







# GET - Get profile for current user
@router.get("/me", response_model=UserProfileResponse)
def read_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_profile = crud_user_profile.get_user_profile_by_user_id(db, user_id=current_user.id)
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found"
        )
    return db_profile





# PUT - Update profile for current user
@router.put("/me", response_model=UserProfileResponse)
def update_my_profile(
    profile_update: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_profile = crud_user_profile.update_user_profile_by_user_id(db, user_id=current_user.id, user_profile_update=profile_update)
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found"
        )
    
    # Trigger meal plan generation automatically
    # print(f"Profile updated for user {current_user.email}. Regenerating meal plan...")
    # try:
    #     generate_meal_plan_for_user(db, current_user.id)
    #     print("Meal plan regenerated successfully.")
    # except Exception as e:
    #     print(f"Error regenerating meal plan: {e}")
    #     # We don't raise an error here to prevent blocking the profile update response
        
    return db_profile









# PATCH - Update Timezone
class TimezoneUpdate(BaseModel):
    timezone: str

@router.patch("/timezone", status_code=status.HTTP_200_OK)
def update_profile_timezone(
    tz_data: TimezoneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the user's timezone.
    """
    profile = crud_user_profile.get_user_profile_by_user_id(db, user_id=current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile.timezone = tz_data.timezone
    db.commit()
    return {"message": "Timezone updated", "timezone": profile.timezone}

# DELETE - Delete all profiles for user