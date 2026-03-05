from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.admin import Admin
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.feast_config import FeastConfig
from app.utils.admin_auth import get_current_admin
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/admin/users", tags=["Admin - Users"])

# Schemas
class UserListItem(BaseModel):
    id: int
    name: str
    email: str
    age: Optional[int] = None
    gender: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserProfileDetail(BaseModel):
    weight: Optional[float]
    height: Optional[float]
    weight_goal: Optional[float]
    fitness_goal: Optional[str]
    activity_level: Optional[str]
    diet_type: Optional[str]
    country: Optional[str]
    calories: Optional[float]
    protein: Optional[float]
    fat: Optional[float]
    carbs: Optional[float]
    
    class Config:
        from_attributes = True

class UserDetail(BaseModel):
    id: int
    name: str
    email: str
    age: Optional[int]
    gender: Optional[str]
    dob: Optional[str]
    profile: Optional[UserProfileDetail]
    active_feasts_count: int = 0
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: List[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int

class PasswordResetRequest(BaseModel):
    new_password: str

# Endpoints
@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """List all users with pagination and search"""
    query = db.query(User)
    
    # Search filter
    if search:
        search_filter = or_(
            User.name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Get total count
    total = query.count()
    
    # Pagination
    offset = (page - 1) * page_size
    users = query.order_by(User.id.desc()).offset(offset).limit(page_size).all()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size
    
    return UserListResponse(
        users=[UserListItem.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{user_id}", response_model=UserDetail)
async def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get detailed user information"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    # Count active feasts
    active_feasts = db.query(func.count(FeastConfig.id)).filter(
        FeastConfig.user_id == user_id,
        FeastConfig.is_active == True
    ).scalar()
    
    user_dict = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "gender": user.gender,
        "dob": str(user.dob) if user.dob else None,
        "profile": UserProfileDetail.model_validate(profile) if profile else None,
        "active_feasts_count": active_feasts or 0
    }
    
    return UserDetail(**user_dict)

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Delete user and all related data (cascade)"""
    try:
        from app.models.chat import ChatSession, ChatHistory
        from app.models.notification import Notification
        from app.models.social_event import SocialEvent
        from app.models.tracking import FoodLog, WorkoutLog, WorkoutSession
        from app.models.meal_plan_history import MealPlanHistory
        from app.models.workout_plan_history import WorkoutPlanHistory
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_email = user.email
        
        # Get user profile ID before deletion
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        profile_id = profile.id if profile else None
        
        # Manually delete all related records to avoid foreign key constraints
        # Delete meal plan history (linked to user_profile_id)
        if profile_id:
            db.query(MealPlanHistory).filter(MealPlanHistory.user_profile_id == profile_id).delete(synchronize_session=False)
            db.query(WorkoutPlanHistory).filter(WorkoutPlanHistory.user_profile_id == profile_id).delete(synchronize_session=False)
        
        # Delete chat history
        db.query(ChatHistory).filter(ChatHistory.user_id == user_id).delete(synchronize_session=False)
        
        # Delete chat sessions
        db.query(ChatSession).filter(ChatSession.user_id == user_id).delete(synchronize_session=False)
        
        # Delete notifications
        db.query(Notification).filter(Notification.user_id == user_id).delete(synchronize_session=False)
        
        # Delete social events
        db.query(SocialEvent).filter(SocialEvent.user_id == user_id).delete(synchronize_session=False)
        
        # Delete food logs
        db.query(FoodLog).filter(FoodLog.user_id == user_id).delete(synchronize_session=False)
        
        # Delete workout logs
        db.query(WorkoutLog).filter(WorkoutLog.user_id == user_id).delete(synchronize_session=False)
        
        # Delete workout sessions
        db.query(WorkoutSession).filter(WorkoutSession.user_id == user_id).delete(synchronize_session=False)
        
        # Now delete the user (cascade will handle profile, feast_configs, feast_meal_overrides)
        db.delete(user)
        db.commit()
        
        return {
            "message": f"User {user_email} deleted successfully",
            "deleted_user_id": user_id
        }
    except Exception as e:
        db.rollback()
        import traceback
        print(f"Error deleting user {user_id}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )

@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    password_data: PasswordResetRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Admin-triggered password reset for a user"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hash the new password using argon2
    from argon2 import PasswordHasher
    ph = PasswordHasher()
    user.password = ph.hash(password_data.new_password)
    
    db.commit()
    
    return {
        "message": f"Password reset successfully for {user.email}",
        "user_id": user_id
    }
