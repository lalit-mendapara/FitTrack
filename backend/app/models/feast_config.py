from sqlalchemy import Column, Integer, String, Boolean, Date, Float, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class FeastConfig(Base):
    __tablename__ = "feast_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Event Details
    event_name = Column(String, nullable=False)
    event_date = Column(Date, nullable=False)
    
    # Banking Configuration
    target_bank_calories = Column(Integer, default=800)
    daily_deduction = Column(Integer, default=200)
    start_date = Column(Date, nullable=False)
    workout_boost_enabled = Column(Boolean, default=True)
    user_selected_deduction = Column(Integer, nullable=True)
    
    # Base Profile Snapshots (for restoration)
    base_calories = Column(Float, nullable=False)
    base_protein = Column(Float, nullable=False)
    base_carbs = Column(Float, nullable=False)
    base_fat = Column(Float, nullable=False)
    
    # State Management
    status = Column(String(20), default="BANKING")  # BANKING / FEAST_DAY / COMPLETED / CANCELLED
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    overrides = relationship("FeastMealOverride", back_populates="feast_config", cascade="all, delete-orphan")
    user = relationship("User", back_populates="feast_configs")

class FeastMealOverride(Base):
    __tablename__ = "feast_meal_overrides"

    id = Column(Integer, primary_key=True, index=True)
    feast_config_id = Column(Integer, ForeignKey("feast_configs.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    override_date = Column(Date, nullable=False)
    meal_id = Column(String, nullable=False)  # "breakfast", "lunch", "dinner", "snacks"
    
    # Adjusted Values
    adjusted_calories = Column(Float, nullable=False)
    adjusted_protein = Column(Float, nullable=False)
    adjusted_carbs = Column(Float, nullable=False)
    adjusted_fat = Column(Float, nullable=False)
    adjusted_portion_size = Column(String, nullable=False)
    
    adjustment_note = Column(String, nullable=True)
    adjustment_method = Column(String(20), default="llm")  # "llm" or "ratio"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    feast_config = relationship("FeastConfig", back_populates="overrides")
    user = relationship("User", back_populates="feast_meal_overrides")

    __table_args__ = (
        UniqueConstraint('feast_config_id', 'override_date', 'meal_id', name='uq_feast_override'),
    )
