# app/models/user_profile.py
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, event
from sqlalchemy.orm import relationship
from datetime import datetime
import logging
from app.database import Base

logger = logging.getLogger(__name__)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)

    # Inputs
    weight = Column(Float)       # Current weight in kg
    height = Column(Float)       # Height in cm
    weight_goal = Column(Float)  # Target weight in kg (e.g., 70.0)
    
    fitness_goal = Column(String(50))   # "weight_loss", "fat_loss", "muscle_gain", "maintenance"
    activity_level = Column(String(50)) # "sedentary", "light", "moderate", "active", "extra_active"
    
    # Calculated Columns (Stored in DB)
    calories = Column(Float, default=0.0)
    protein = Column(Float, default=0.0)
    fat = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)
    
    # Personal info & Timestamps
    country = Column(String(100))
    diet_type = Column(String(50))  # "veg" or "non_veg"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_physical_update = Column(DateTime, default=datetime.utcnow)
    timezone = Column(String(50), default="UTC") # e.g. "Asia/Kolkata"
    
    # Relationship to User (which contains age and gender)
    user = relationship("User", back_populates="profile")
    meal_plan = relationship("MealPlan", back_populates="user_profile", cascade="all, delete")
    workout_preferences = relationship("WorkoutPreferences", back_populates="user_profile", uselist=False, cascade="all, delete")
    workout_plan = relationship("WorkoutPlan", back_populates="user_profile", uselist=False, cascade="all, delete")


# --- CALCULATION ENGINE ---

# --- CALCULATION ENGINE MOVED TO SERVICE ---
# Please refer to app.services.nutrition_service for calculation logic.
from app.services.nutrition_service import calculate_daily_targets

def apply_nutrition_plan(target):
    """
    Applies calculated nutrition targets to the UserProfile instance.
    Uses the external nutrition_service to keep this model file clean.
    """
    logger.info(f"Refreshing nutrition plan for profile {getattr(target, 'id', 'new')}")
    
    if getattr(target, 'skip_macro_calculation', False):
        logger.info("Skipping macro calculation due to manual override flag.")
        return
        
    # Ensure minimum data
    if not all([target.weight, target.height]):
        return

    # Extract clean arguments for the service
    # Note: Accessing relationship attributes (target.user) inside an event listener 
    # might trigger a lazy load or be None if not yet flushed.
    # We handle this gracefully.
    age = 25
    gender = 'male'
    
    if target.user:
        age = getattr(target.user, 'age', 25)
        gender = getattr(target.user, 'gender', 'male')
        
    # Call Service
    results = calculate_daily_targets(
        weight=target.weight,
        height=target.height,
        age=age,
        gender=gender,
        activity_level=target.activity_level,
        fitness_goal=target.fitness_goal,
        diet_type=target.diet_type, 
        weight_goal=target.weight_goal
    )
    
    # Apply results
    # Apply results ONLY if changed (to prevent spurious updated_at bumps)
    
    def is_diff(attr, new_val):
        old_val = getattr(target, attr, 0.0) or 0.0
        # Check tolerance for floats
        return abs(old_val - new_val) > 0.1

    if is_diff('calories', results['calories']):
        target.calories = results['calories']
    if is_diff('protein', results['protein']):
        target.protein = results['protein']
    if is_diff('fat', results['fat']):
        target.fat = results['fat']
    if is_diff('carbs', results['carbs']):
        target.carbs = results['carbs']


# --- AUTOMATION LISTENERS ---

@event.listens_for(UserProfile, 'before_insert')
def receive_before_insert(mapper, connection, target):
    logger.info(f"Before insert event triggered for new profile")
    apply_nutrition_plan(target)

@event.listens_for(UserProfile, 'before_update')
def receive_before_update(mapper, connection, target):
    logger.info(f"Before update event triggered for profile {getattr(target, 'id', 'unknown')}")
    
    # Check if physical stats changed
    physical_fields = ['weight', 'height', 'weight_goal', 'fitness_goal', 'activity_level', 'diet_type', 'country']
    physical_changed = False
    
    for field in physical_fields:
        # SQLAlchemy history inspection
        from sqlalchemy.orm import attributes
        history = attributes.get_history(target, field)
        if history.has_changes():
            physical_changed = True
            break
            
    if physical_changed:
        target.last_physical_update = datetime.utcnow()
        
    apply_nutrition_plan(target)