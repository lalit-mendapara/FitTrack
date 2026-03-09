from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import List, Optional
from datetime import datetime, date
from app.database import get_db
from app.models.admin import Admin
from app.models.feast_config import FeastConfig, FeastMealOverride
from app.models.user import User
from app.utils.admin_auth import get_current_admin
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin/feasts", tags=["Admin - Feasts"])

class FeastListItem(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: str
    event_name: str
    event_date: date
    status: str
    daily_deduction: int
    target_bank_calories: int
    start_date: date
    workout_boost_enabled: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class FeastListResponse(BaseModel):
    feasts: List[FeastListItem]
    total: int
    page: int
    page_size: int
    total_pages: int

class MealOverrideDetail(BaseModel):
    id: int
    override_date: date
    meal_id: str
    adjusted_calories: float
    adjusted_protein: float
    adjusted_carbs: float
    adjusted_fat: float
    adjusted_portion_size: str
    adjustment_note: Optional[str]
    adjustment_method: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class FeastDetail(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: str
    event_name: str
    event_date: date
    target_bank_calories: int
    daily_deduction: int
    start_date: date
    workout_boost_enabled: bool
    user_selected_deduction: Optional[int]
    feast_workout_data: Optional[dict]
    selected_meals: Optional[List[str]]
    original_diet_snapshot: Optional[dict]
    base_calories: float
    base_protein: float
    base_carbs: float
    base_fat: float
    status: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    overrides: List[MealOverrideDetail]
    days_until_event: int
    total_banking_days: int
    projected_banked_calories: int
    
    class Config:
        from_attributes = True

@router.get("", response_model=FeastListResponse)
async def list_feasts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """List all feast configurations with pagination and filters"""
    query = db.query(FeastConfig).join(User, FeastConfig.user_id == User.id)
    
    if search:
        search_filter = or_(
            FeastConfig.event_name.ilike(f"%{search}%"),
            User.name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    if status_filter:
        query = query.filter(FeastConfig.status == status_filter)
    
    if is_active is not None:
        query = query.filter(FeastConfig.is_active == is_active)
    
    total = query.count()
    
    offset = (page - 1) * page_size
    feasts = query.order_by(FeastConfig.created_at.desc()).offset(offset).limit(page_size).all()
    
    total_pages = (total + page_size - 1) // page_size
    
    feast_items = []
    for feast in feasts:
        user = db.query(User).filter(User.id == feast.user_id).first()
        feast_items.append(FeastListItem(
            id=feast.id,
            user_id=feast.user_id,
            user_name=user.name if user else "Unknown",
            user_email=user.email if user else "Unknown",
            event_name=feast.event_name,
            event_date=feast.event_date,
            status=feast.status,
            daily_deduction=feast.daily_deduction,
            target_bank_calories=feast.target_bank_calories,
            start_date=feast.start_date,
            workout_boost_enabled=feast.workout_boost_enabled,
            is_active=feast.is_active,
            created_at=feast.created_at
        ))
    
    return FeastListResponse(
        feasts=feast_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{feast_id}", response_model=FeastDetail)
async def get_feast_detail(
    feast_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get detailed information about a specific feast configuration"""
    feast = db.query(FeastConfig).filter(FeastConfig.id == feast_id).first()
    
    if not feast:
        raise HTTPException(status_code=404, detail="Feast configuration not found")
    
    user = db.query(User).filter(User.id == feast.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    overrides = db.query(FeastMealOverride).filter(
        FeastMealOverride.feast_config_id == feast_id
    ).order_by(FeastMealOverride.override_date.desc()).all()
    
    override_details = [MealOverrideDetail.model_validate(ov) for ov in overrides]
    
    today = date.today()
    days_until_event = (feast.event_date - today).days
    total_banking_days = (feast.event_date - feast.start_date).days
    
    days_elapsed = (today - feast.start_date).days if today >= feast.start_date else 0
    days_elapsed = max(0, min(days_elapsed, total_banking_days))
    projected_banked_calories = days_elapsed * feast.daily_deduction
    
    return FeastDetail(
        id=feast.id,
        user_id=feast.user_id,
        user_name=user.name,
        user_email=user.email,
        event_name=feast.event_name,
        event_date=feast.event_date,
        target_bank_calories=feast.target_bank_calories,
        daily_deduction=feast.daily_deduction,
        start_date=feast.start_date,
        workout_boost_enabled=feast.workout_boost_enabled,
        user_selected_deduction=feast.user_selected_deduction,
        feast_workout_data=feast.feast_workout_data,
        selected_meals=feast.selected_meals,
        original_diet_snapshot=feast.original_diet_snapshot,
        base_calories=feast.base_calories,
        base_protein=feast.base_protein,
        base_carbs=feast.base_carbs,
        base_fat=feast.base_fat,
        status=feast.status,
        is_active=feast.is_active,
        created_at=feast.created_at,
        updated_at=feast.updated_at,
        overrides=override_details,
        days_until_event=days_until_event,
        total_banking_days=total_banking_days,
        projected_banked_calories=projected_banked_calories
    )

@router.get("/stats/summary")
async def get_feast_stats(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get summary statistics for feast mode usage"""
    total_feasts = db.query(func.count(FeastConfig.id)).scalar()
    active_feasts = db.query(func.count(FeastConfig.id)).filter(
        FeastConfig.is_active == True
    ).scalar()
    banking_feasts = db.query(func.count(FeastConfig.id)).filter(
        FeastConfig.status == "BANKING"
    ).scalar()
    completed_feasts = db.query(func.count(FeastConfig.id)).filter(
        FeastConfig.status == "COMPLETED"
    ).scalar()
    cancelled_feasts = db.query(func.count(FeastConfig.id)).filter(
        FeastConfig.status == "CANCELLED"
    ).scalar()
    
    avg_deduction = db.query(func.avg(FeastConfig.daily_deduction)).filter(
        FeastConfig.is_active == True
    ).scalar() or 0
    
    return {
        "total_feasts": total_feasts,
        "active_feasts": active_feasts,
        "banking_feasts": banking_feasts,
        "completed_feasts": completed_feasts,
        "cancelled_feasts": cancelled_feasts,
        "average_daily_deduction": round(avg_deduction, 2)
    }
