from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_profile_id = Column(Integer, ForeignKey('user_profiles.id', ondelete="CASCADE"), nullable=False, index=True)

    plan_name = Column(String)
    duration_weeks = Column(Integer)
    primary_goal = Column(String)

    # JSON Fields for complex data
    weekly_schedule = Column(JSONB, nullable=False)
    progression_guidelines = Column(JSONB)
    cardio_recommendations = Column(JSONB)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user_profile = relationship("UserProfile", back_populates="workout_plan")
