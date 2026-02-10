from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.services.social_event_service import get_active_event
from pydantic import BaseModel
from datetime import date
from typing import Optional

router = APIRouter(prefix="/social-events", tags=["social-events"])

class SocialEventResponse(BaseModel):
    event_name: str
    event_date: date
    target_bank_calories: int
    daily_deduction: int
    start_date: date
    days_remaining: int
    status: str # "BANKING" or "FEAST_DAY" or "COMPLETED"

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
