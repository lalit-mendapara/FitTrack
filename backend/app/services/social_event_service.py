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
