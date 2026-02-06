# app/schemas/user_profile.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserProfileBase(BaseModel):
    weight: float = Field(..., gt=0, description="Current weight in kg")
    height: float = Field(..., gt=0, description="Height in cm")
    weight_goal: float = Field(..., gt=0, description="Target weight in kg")
    
    fitness_goal: str = Field(
        ..., 
        pattern="^(weight_loss|fat_loss|muscle_gain|maintenance)$",
        description="weight_loss, fat_loss, muscle_gain, or maintenance"
    )
    activity_level: str = Field(
        ..., 
        pattern="^(sedentary|light|moderate|active|extra_active)$",
        description="sedentary, light, moderate, active, or extra_active"
    )
    
    country: Optional[str] = None
    diet_type: str = Field(
        ..., 
        pattern="^(veg|non_veg|both)$",
        description="veg, non_veg, or both"
    )

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileUpdate(BaseModel):
    weight: Optional[float] = Field(None, gt=0, description="Current weight in kg")
    height: Optional[float] = Field(None, gt=0, description="Height in cm")
    weight_goal: Optional[float] = Field(None, gt=0, description="Target weight in kg")
    
    fitness_goal: Optional[str] = Field(
        None, 
        pattern="^(weight_loss|fat_loss|muscle_gain|maintenance)$",
        description="weight_loss, fat_loss, muscle_gain, or maintenance"
    )
    activity_level: Optional[str] = Field(
        None, 
        pattern="^(sedentary|light|moderate|active|extra_active)$",
        description="sedentary, light, moderate, active, or extra_active"
    )
    
    country: Optional[str] = None
    diet_type: Optional[str] = Field(
        None,
        pattern="^(veg|non_veg|both)$",
        description="veg, non_veg, or both"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "weight": 85.5,
                "height": 180.0,
                "weight_goal": 75.0,
                "fitness_goal": "fat_loss",
                "activity_level": "moderate",
                "country": "USA",
                "diet_type": "non_veg"
            }
        }

class UserProfileRequest(UserProfileBase):
    """Alias for backward compatibility"""
    pass

class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    
    # Input data
    weight: float
    height: float
    weight_goal: float
    fitness_goal: str
    activity_level: str
    
    # Automated Calculations (From SQLAlchemy events)
    calories: float
    protein: float
    fat: float
    carbs: float
    
    # Meta
    country: Optional[str]
    diet_type: str
    created_at: datetime
    updated_at: datetime
    last_physical_update: Optional[datetime]

    class Config:
        from_attributes = True