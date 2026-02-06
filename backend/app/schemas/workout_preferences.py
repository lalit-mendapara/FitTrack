from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class WorkoutPreferencesBase(BaseModel):
    experience_level: str = Field(..., description="beginner, intermediate, advanced")
    days_per_week: int = Field(..., ge=1, le=7, description="Number of workout days per week")
    session_duration_min: int = Field(..., gt=0, description="Session duration in minutes")
    health_restrictions: Optional[str] = Field("none", description="Any health restrictions")

class WorkoutPreferencesCreate(WorkoutPreferencesBase):
    pass

class WorkoutPreferencesUpdate(BaseModel):
    experience_level: Optional[str] = None
    days_per_week: Optional[int] = Field(None, ge=1, le=7)
    session_duration_min: Optional[int] = Field(None, gt=0)
    health_restrictions: Optional[str] = None

class WorkoutPreferencesResponse(WorkoutPreferencesBase):
    id: int
    user_profile_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
