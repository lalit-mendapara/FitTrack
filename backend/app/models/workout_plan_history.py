from datetime import datetime
from sqlalchemy import (
    Column, Integer, ForeignKey, DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base

class WorkoutPlanHistory(Base):
    __tablename__ = "workout_plan_history"

    id = Column(Integer, primary_key=True, index=True)

    # Reference to correct user profile
    user_profile_id = Column(
        Integer,
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Stores the full snapshot of the generated plan
    # This includes exercises, sets, reps, cardio, etc.
    workout_plan_snapshot = Column(
        JSONB,
        nullable=False,
        comment="Snapshot of the generated workout plan (schedule object)"
    )

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship back to profile
    user_profile = relationship(
        "UserProfile",
        backref="workout_history"
    )
