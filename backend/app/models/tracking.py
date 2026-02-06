from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base

class FoodLog(Base):
    __tablename__ = "food_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=date.today)
    
    # Logged Item
    food_name = Column(String(100))
    meal_type = Column(String(50), nullable=True) # e.g. Breakfast, Lunch, Dinner
    calories = Column(Float, default=0.0)
    protein = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)
    fat = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.now)

class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=date.today)
    
    # Logged Activity
    exercise_name = Column(String(100))
    img_url = Column(String(255), nullable=True)
    
    # Detailed Metrics
    sets = Column(String(50), nullable=True) # e.g. "3x12"
    reps = Column(String(50), nullable=True) # Can be redundant if inside sets, but keeping flexible
    weight = Column(Float, nullable=True) # Weight in kg/lbs
    muscle_group = Column(String(50), nullable=True)
    
    # Optional metrics
    duration_min = Column(Integer, nullable=True)
    calories_burned = Column(Float, nullable=True)
    notes = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)

class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, default=date.today)
    
    # Session Details
    duration_minutes = Column(Integer, nullable=False, default=0)
    
    created_at = Column(DateTime, default=datetime.now)
