from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class SocialEvent(Base):
    __tablename__ = "social_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Event Details
    event_name = Column(String, nullable=False)          # e.g., "Pizza Night", "Wedding"
    event_date = Column(Date, nullable=False)            # e.g., 2026-02-14
    
    # Banking Strategy
    target_bank_calories = Column(Integer, default=800)  # Total calories to save (e.g., 800)
    daily_deduction = Column(Integer, default=200)       # Daily reduction amount (e.g., 200)
    start_date = Column(Date, nullable=False)            # When the banking starts
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="social_events")
