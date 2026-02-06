from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.notification import Notification
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter(prefix="/notifications", tags=["Notifications"])

class NotificationResponse(BaseModel):
    id: int
    message: str
    is_read: bool
    type: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/unread", response_model=List[NotificationResponse])
def get_unread_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all unread notifications for the current user.
    """
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).order_by(Notification.created_at.desc()).all()
    
    return notifications

@router.post("/{notification_id}/read", status_code=status.HTTP_200_OK)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a notification as read.
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read"}
