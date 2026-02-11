from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.models.social_event import SocialEvent
from app.models.user_profile import UserProfile
import logging

logger = logging.getLogger(__name__)

def propose_banking_strategy(db: Session, user_id: int, event_date: date, event_name: str):
    """
    Calculates a proposed banking strategy for a future event.
    Returns a dict with the proposal details.
    """
    today = date.today()
    days_until = (event_date - today).days
    
    if days_until <= 0:
        return {"error": "Event must be in the future"}
        
    if days_until > 14:
        return {"error": "Event is too far away (max 2 weeks)"}

    # Default logic: Target 800-1000 kcal buffer
    # Calculate daily deduction needed
    target_bank = 800
    daily_deduction = int(target_bank / days_until)
    
    # Safety Check: Don't deduct too much
    # Improve logic: Get user BMR/TDEE and ensure we don't drop below unsafe levels
    # For MVP, cap deduction at 500 kcal/day
    if daily_deduction > 500:
        target_bank = 500 * days_until # Reduce goal if time is short
        daily_deduction = 500
    
    # Round to nearest 50
    daily_deduction = round(daily_deduction / 50) * 50
    target_bank = daily_deduction * days_until
    
    return {
        "event_name": event_name,
        "event_date": event_date,
        "days_remaining": days_until,
        "daily_deduction": daily_deduction,
        "total_banked": target_bank,
        "start_date": today
    }

def create_social_event(db: Session, user_id: int, proposal: dict):
    """
    Persists the social event to DB.
    """
    # Deactivate any existing active events to avoid double-banking
    existing = db.query(SocialEvent).filter(
        SocialEvent.user_id == user_id, 
        SocialEvent.is_active == True
    ).first()
    
    if existing:
        existing.is_active = False
    
    new_event = SocialEvent(
        user_id=user_id,
        event_name=proposal["event_name"],
        event_date=proposal["event_date"],
        target_bank_calories=proposal["total_banked"],
        daily_deduction=proposal["daily_deduction"],
        start_date=proposal["start_date"],
        is_active=True
    )
    
    db.add(new_event)
    db.commit()
    return new_event

def get_active_event(db: Session, user_id: int, current_date: date = None) -> SocialEvent:
    """
    Get the currently active event for a user.
    Handles auto-expiry if event date is passed.
    """
    if not current_date:
        current_date = date.today()
        
    event = db.query(SocialEvent).filter(
        SocialEvent.user_id == user_id,
        SocialEvent.is_active == True,
        SocialEvent.event_date >= current_date # Still relevant
    ).first()
    
    return event

def get_effective_daily_targets(db: Session, user_id: int, base_targets: dict, current_date: date) -> dict:
    """
    Calculates effective targets based on active social events.
    Returns Modified Targets (or original if no event).
    """
    event = get_active_event(db, user_id, current_date)
    
    if not event:
        return base_targets
        
    effective = base_targets.copy()
    
    # Scenario 1: Buffer Phase (Before Event)
    if event.start_date <= current_date < event.event_date:
        deduction = event.daily_deduction
        effective['calories'] -= deduction
        
        # Smart Macro Reduction
        # Reduce Carbs & Fat mostly, keep Protein high
        # Protein protection: Only reduce if strictly necessary? 
        # For simplicity MVP: Reduce proportional to Calorie reduction
        ratio = effective['calories'] / (base_targets['calories'] + 0.1) # avoid div0
        
        # Keep protein as high as possible (maybe only 10% reduction if needed)
        # But `ratio` applies to all. Let's do better.
        
        # Reduce Carbs/Fat by the calorie amount
        # 1g Carb = 4, 1g Fat = 9
        # Split deduction 60% Carbs, 40% Fat
        carb_cals_dropped = deduction * 0.6
        fat_cals_dropped = deduction * 0.4
        
        effective['carbs'] -= (carb_cals_dropped / 4)
        effective['fat'] -= (fat_cals_dropped / 9)
        
        # Safety floors
        effective['carbs'] = max(effective['carbs'], 50)
        effective['fat'] = max(effective['fat'], 20)
        
        return effective

    # Scenario 2: Feast Day (Event Date)
    elif current_date == event.event_date:
        bonus = event.target_bank_calories
        effective['calories'] += bonus
        
        # Where does the bonus go? Mostly Carbs/Fat for the party
        # Let's say 50/50
        effective['carbs'] += (bonus * 0.5 / 4)
        effective['fat'] += (bonus * 0.5 / 9)
        
        # Auto-expire event after today (handled by logic or cron, strictly query filters >= today so tomorrow it won't show)
        # We can also update is_active=False here if we want strict cleanup
        
        return effective
        
    return base_targets

# --- NEW: CANCEL / UNDO LOGIC ---
def cancel_active_event(db: Session, user_id: int):
    """
    Cancels the currently active social event and restores the user's plan.
    Does NOT modify UserProfile directly, but triggers logic to fix today's meals.
    """
    today = date.today()
    event = get_active_event(db, user_id, today)
    
    if not event:
        return {"error": "No active event found to cancel."}
    
    # 1. Capture what phase we are in (Banking vs Feast)
    # This determines if we need to ADD back calories (Undo Banking) or REMOVE bonus (Undo Feast)
    is_feast_day = (today == event.event_date)
    is_banking = (event.start_date <= today < event.event_date)
    
    restore_amount = 0
    if is_banking:
        restore_amount = event.daily_deduction  # We need to ADD this back
    elif is_feast_day:
        restore_amount = -event.target_bank_calories # We need to REMOVE this bonus
    
    # 2. Deactivate Event
    event.is_active = False
    
    # 3. Get User's Base Targets (The "Normal" Plan)
    # Since UserProfile stores the base targets (unless modified by other logic, but we assume
    # the system uses `get_effective_daily_targets` dynamically), we just need to get the
    # current UserProfile targets.
    # WAIT: UserProfile MIGHT have been modified if the user confirmed the event?
    # No, `create_social_event` didn't modify UserProfile.
    # `ai_coach.py` called `patch_todays_meal_plan` which modified MEAL portions.
    # So `patch_todays_meal_plan` used a `new_target`.
    # To RESTORE, we just need to call `adjust_todays_meal_plan` with the BASE target from UserProfile.
    
    from app.services.stats_service import StatsService
    stats_service = StatsService(db)
    # Note: stats_service.get_user_profile calls get_effective_daily_targets internally!
    # We want the RAW UserProfile.
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        db.commit() # Save the deactivation
        return {"message": "Event cancelled, but profile not found."}
        
    base_target = profile.calories
    
    # 4. Trigger Meal Plan Restoration
    # We call adjust_todays_meal_plan with the BASE target.
    # Since the event is now inactive, this target is the "correct" one.
    # The adjust logic will see (Target > Planned) and scale UP.
    
    # We need to know which meals are eaten to avoid patching them.
    from app.models.tracking import FoodLog
    logs = db.query(FoodLog).filter(FoodLog.user_id == user_id, FoodLog.date == today).all()
    completed_meals = list(set([l.meal_type.lower() for l in logs]))
    
    db.commit() # Commit cancellation first
    
    from app.services.meal_service import adjust_todays_meal_plan
    
    # Run Adjustment
    # Note: `adjust_todays_meal_plan` commits its own changes.
    adjust_result = adjust_todays_meal_plan(db, user_id, base_target, completed_meals)
    
    return {
        "message": f"Feast Mode deactivated. {adjust_result.get('message', '')}",
        "restored_calories": restore_amount,
        "adjust_details": adjust_result
    }
