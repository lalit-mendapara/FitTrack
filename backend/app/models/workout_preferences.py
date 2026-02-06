from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class WorkoutPreferences(Base):
    __tablename__ = "workout_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_profile_id = Column(Integer, ForeignKey('user_profiles.id'), unique=True, nullable=False)

    # Preferences
    experience_level = Column(String(50))   # "beginner", "intermediate", "advanced"
    days_per_week = Column(Integer)
    session_duration_min = Column(Integer)
    health_restrictions = Column(String(255), nullable=True) # "none" or specific text

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to UserProfile
    user_profile = relationship("UserProfile", back_populates="workout_preferences")
