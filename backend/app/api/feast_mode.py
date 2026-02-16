from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.services.feast_mode_manager import FeastModeManager
from app.schemas.feast_mode import (
    FeastProposalRequest,
    FeastActivateRequest,
    FeastUpdateRequest,
    FeastStatusResponse,
    FeastStatusResponse,
    FeastOverrideResponse,
    FeastPreCheckRequest,
    FeastPreCheckResponse,
    FeastDeactivationPreviewResponse
)

router = APIRouter(prefix="/feast-mode", tags=["Feast Mode"])

from app.models.user import User
from app.api.auth import get_current_user
from app.models.tracking import FoodLog
from sqlalchemy import func

@router.post("/deactivate-preview", response_model=FeastDeactivationPreviewResponse)
def deactivate_preview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns preview of what happens if Feast Mode is cancelled.
    """
    user_id = current_user.id
    manager = FeastModeManager(db)
    preview = manager.get_deactivation_preview(user_id)
    
    if not preview or "error" in preview:
        raise HTTPException(status_code=400, detail=preview.get("error", "No active config"))
        
    return preview

@router.post("/pre-activate-check", response_model=FeastPreCheckResponse)
def pre_activate_check(
    request: FeastPreCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Checks if activating Feast Mode today would result in dangerously low remaining calories.
    """
    today = date.today()
    
    # Only relevant if start_date matches today
    if request.start_date != today:
        return FeastPreCheckResponse(
            warning=False,
            calories_consumed=0,
            remaining_after_deduction=2000, # Dummy, not used
            safe_minimum=0
        )
        
    # 1. Calculate Consumed Calories Today
    logs = db.query(FoodLog).filter(
        FoodLog.user_id == current_user.id,
        FoodLog.date == today
    ).all()
    
    consumed = sum(l.calories for l in logs) if logs else 0
    
    # 2. Determine Base Stats
    base = request.base_calories
    if not base:
        # Fetch from Manager logic (which checks Meal Plan first)
        manager = FeastModeManager(db)
        # We can use get_effective_targets but that needs an ACTIVE config.
        # So we replicate the "Pre-Activation" logic
        from app.models.user_profile import UserProfile
        from app.models.meal_plan import MealPlan
        
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        base = profile.calories if profile else 2000
        
        plan = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).first() if profile else None
        if plan and plan.daily_generated_totals:
             totals = plan.daily_generated_totals
             if isinstance(totals, dict):
                 base = totals.get("calories", base)
             elif hasattr(totals, "calories"):
                 base = totals.calories
                 
    # 3. Calculate Remaining if Activated
    effective_target = base - request.daily_deduction
    remaining = effective_target - consumed
    
    # 4. Determine Warning
    SAFE_MINIMUM = 500  # Minimum calories allowed for remaining part of day? 
    # Or should we check total daily minimum?
    # Let's say: If remaining is < 200, user will starve.
    
    warning = False
    msg = None
    
    if remaining < 200:
        warning = True
        msg = f"Warning: You have already eaten {int(consumed)} kcal. Activating now would leave you with only {int(remaining)} kcal for the rest of the day!"
    elif remaining < 0:
        warning = True
        msg = f"Critical: You have already exceeded the target! Activating involves a deficit of {int(abs(remaining))} kcal."
        
    return FeastPreCheckResponse(
        warning=warning,
        message=msg,
        calories_consumed=consumed,
        remaining_after_deduction=remaining,
        safe_minimum=200
    )

# ... (router definition)

@router.get("/status", response_model=Optional[FeastStatusResponse])
def get_feast_status(
    current_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    manager = FeastModeManager(db)
    config = manager.get_active_config(user_id, current_date or date.today())
    
    if not config:
        return None
        
    days_remaining = (config.event_date - (current_date or date.today())).days
    
    # Calculate effective calories for display
    effective = manager.get_effective_targets(user_id, current_date or date.today())
    
    return FeastStatusResponse(
        event_name=config.event_name,
        event_date=config.event_date,
        status=config.status,
        daily_deduction=config.daily_deduction,
        target_bank_calories=config.target_bank_calories,
        days_remaining=days_remaining,
        start_date=config.start_date,
        base_calories=config.base_calories,
        effective_calories=effective["calories"],
        workout_boost_enabled=config.workout_boost_enabled
    )

@router.post("/propose")
def propose_feast(
    request: FeastProposalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    manager = FeastModeManager(db)
    proposal = manager.propose_strategy(
        user_id=user_id,
        event_date=request.event_date,
        event_name=request.event_name,
        custom_deduction=request.custom_deduction
    )
    
    if "error" in proposal:
        raise HTTPException(status_code=400, detail=proposal["error"])
        
    return proposal

@router.post("/activate")
def activate_feast(
    request: FeastActivateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    manager = FeastModeManager(db)
    
    # Reconstruct proposal dict
    proposal = {
        "event_name": request.event_name,
        "event_date": request.event_date,
        "daily_deduction": request.daily_deduction,
        "total_banked": request.total_banked,
        "start_date": request.start_date,
        "custom_deduction": request.custom_deduction
    }
    
    try:
        config = manager.activate(
            user_id, 
            proposal, 
            request.workout_boost,
            workout_preference=request.workout_preference
        )
        return {"message": "Feast Mode activated", "config_id": config.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel")
def cancel_feast(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    manager = FeastModeManager(db)
    result = manager.cancel(user_id)
    return result

@router.patch("/update")
def update_feast(
    request: FeastUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    manager = FeastModeManager(db)
    result = manager.update_mid_day(
        user_id=user_id,
        new_deduction=request.daily_deduction,
        workout_boost=request.workout_boost
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@router.get("/overrides", response_model=List[FeastOverrideResponse])
def get_overrides(
    target_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    manager = FeastModeManager(db)
    overrides_map = manager.get_overrides_for_date(user_id, target_date or date.today())
    
    return [
        FeastOverrideResponse(
            meal_id=ov.meal_id,
            adjusted_calories=ov.adjusted_calories,
            adjusted_protein=ov.adjusted_protein,
            adjusted_carbs=ov.adjusted_carbs,
            adjusted_fat=ov.adjusted_fat,
            adjusted_portion_size=ov.adjusted_portion_size,
            adjustment_note=ov.adjustment_note,
            adjustment_method=ov.adjustment_method
        )
        for ov in overrides_map.values()
    ]
