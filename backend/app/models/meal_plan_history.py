from datetime import datetime
from sqlalchemy import (
    Column, Integer, ForeignKey, DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base

class MealPlanHistory(Base):
    __tablename__ = "meal_plan_history"

    id = Column(Integer, primary_key=True, index=True)

    # Reference to correct user profile
    user_profile_id = Column(
        Integer,
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Stores the full snapshot of the generated plan
    # This includes dish names, portion sizes, nutrients, etc.
    meal_plan_snapshot = Column(
        JSONB,
        nullable=False,
        comment="Snapshot of the generated meal plan (list of meal objects)"
    )

    created_at = Column(DateTime, default=datetime.utcnow)

    user_profile = relationship(
        "UserProfile",
        backref="history"
    )
