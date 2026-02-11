from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.services.social_event_service import (
    get_active_event, 
    propose_banking_strategy, 
    create_social_event, 
    cancel_active_event
)
from app.services.workout_service import patch_limit_day_workout, restore_workout_plan
from app.services.meal_service import adjust_todays_meal_plan
from app.services.stats_service import StatsService
from app.models.tracking import FoodLog
from pydantic import BaseModel
from datetime import date
from typing import Optional, Dict, Any

router = APIRouter(prefix="/social-events", tags=["social-events"])

# --- Schemas ---

class SocialEventRequest(BaseModel):
    event_name: str
    event_date: date

class SocialEventProposal(BaseModel):
    event_name: str
    event_date: date
    days_remaining: int
    daily_deduction: int
    total_banked: int
    start_date: date

class SocialEventResponse(BaseModel):
    event_name: str
    event_date: date
    target_bank_calories: int
    daily_deduction: int
    start_date: date
    days_remaining: int
    status: str # "BANKING" or "FEAST_DAY" or "COMPLETED"

# --- Endpoints ---

@router.get("/active", response_model=Optional[SocialEventResponse])
def get_active_social_event(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the currently active social event/buffer for the user.
    """
    event = get_active_event(db, current_user.id)
    
    if not event:
        return None
        
    today = date.today()
    status = "BANKING"
    if today == event.event_date:
        status = "FEAST_DAY"
    elif today > event.event_date:
        status = "COMPLETED" # Should ideally be filtered out by service, but safety check
        
    days_remaining = (event.event_date - today).days
    
    return {
        "event_name": event.event_name,
        "event_date": event.event_date,
        "target_bank_calories": event.target_bank_calories,
        "daily_deduction": event.daily_deduction,
        "start_date": event.start_date,
        "days_remaining": max(0, days_remaining),
        "status": status
    }

@router.post("/propose", response_model=Dict[str, Any])
def propose_event(
    request: SocialEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate a banking strategy for a potential event.
    Returns the proposal (math) without saving.
    """
    proposal = propose_banking_strategy(db, current_user.id, request.event_date, request.event_name)
    
    if "error" in proposal:
        raise HTTPException(status_code=400, detail=proposal["error"])
        
    return proposal

@router.post("/confirm", response_model=SocialEventResponse)
def confirm_event(
    proposal: SocialEventProposal,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Activate a Feast Mode event.
    1. Saves event to DB.
    2. Patches Workout Plan (Glycogen Depletion).
    3. Patches Today's Meal Plan (if deduction starts today).
    """
    # 1. Create Event
    # Convert Pydantic model to dict
    proposal_dict = proposal.dict()
    event = create_social_event(db, current_user.id, proposal_dict)
    
    # 2. Patch Workout
    try:
        patch_limit_day_workout(db, current_user.id, event.event_date)
    except Exception as e:
        print(f"Warning: Failed to patch workout: {e}")
        # Non-blocking, continue
        
    # 3. Patch Today's Meals (If we need to start banking TODAY)
    # We check if effective target changed.
    stats = StatsService(db)
    # This call now includes the newly created event in calculation!
    # Because get_user_profile -> get_effective_daily_targets -> get_active_event
    input_profile = stats.get_user_profile(current_user.id)
    new_target = input_profile["caloric_target"]
    
    # Simple check: If deduction is active, we patch.
    # Logic: adjust_todays_meal_plan works bidirectionally.
    # It will detect if New Target < Planned and scale down.
    
    try:
        today = date.today()
        # Fetch completed meals for robust patching
        logs = db.query(FoodLog).filter(FoodLog.user_id == current_user.id, FoodLog.date == today).all()
        completed_meals = list(set([l.meal_type.lower() for l in logs]))
        
        adjust_todays_meal_plan(db, current_user.id, new_target, completed_meals)
    except Exception as e:
        print(f"Warning: Failed to patch meals: {e}")

    # Return formatted response
    days_remaining = (event.event_date - date.today()).days
    return {
        "event_name": event.event_name,
        "event_date": event.event_date,
        "target_bank_calories": event.target_bank_calories,
        "daily_deduction": event.daily_deduction,
        "start_date": event.start_date,
        "days_remaining": max(0, days_remaining),
        "status": "BANKING"
    }

@router.post("/cancel")
def cancel_event(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deactivate the current event and restore plans.
    1. Sets is_active = False
    2. Restores Meal Plan (Scales Up)
    3. Restores Workout Plan (Reverts Depletion)
    """
    # Get active event date before cancelling (for workout restore)
    active_event = get_active_event(db, current_user.id)
    event_date = active_event.event_date if active_event else None
    
    # 1. Cancel & Restore Meals
    # This function handles DB deactivation and Meal Plan scaling/restoring
    result = cancel_active_event(db, current_user.id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    # 2. Restore Workout
    if event_date:
        try:
            restore_workout_plan(db, current_user.id, event_date)
        except Exception as e:
            print(f"Warning: Failed to restore workout: {e}")
            
    return result
