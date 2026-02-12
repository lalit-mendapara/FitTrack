from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)

    # 🔑 FK reference
    user_profile_id = Column(
        Integer,
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    meal_id = Column(String, nullable=False)
    label = Column(String, nullable=False)
    is_veg = Column(Boolean, nullable=False)

    dish_name = Column(String, nullable=False)
    portion_size = Column(String, nullable=False)

    # JSON fields
    nutrients = Column(
        JSONB,
        nullable=False,
        comment="Macros: { p, c, f }"
    )

    alternatives = Column(
        JSONB,
        nullable=True,
        comment="Alternative dishes"
    )

    guidelines = Column(
        JSONB,
        nullable=True,
        comment=" Guidelines for the meal plan"
        # Example:
        # ["Drink 3L water", "No sugar", "Walk 8k steps"]
    )

    feast_notes = Column(
        JSONB,
        nullable=True,
        comment="Feast Mode per-meal notes"
        # Example:
        # ["Reduced 50 kcal - carbs trimmed for banking"]
    )

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_profile = relationship(
        "UserProfile",
        back_populates="meal_plan"
    )
