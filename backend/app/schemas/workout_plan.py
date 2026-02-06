from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime

class ExerciseDetail(BaseModel):
    exercise: str
    sets: int
    reps: Union[str, int]
    rest_sec: int
    image_url: Optional[str] = None
    calories_burned: Optional[float] = 0.0
    instructions: Optional[str] = None

class DaySchedule(BaseModel):
    day_name: str
    workout_name: Optional[str] = "Workout Session"
    primary_muscle_group: Optional[str] = "General"
    focus: Optional[str] = None
    exercises: Optional[List[ExerciseDetail]] = None
    cardio: Optional[str] = None
    session_duration_min: Optional[int] = None
    activities: Optional[List[str]] = None # For rest/recovery days

class WeeklySchedule(BaseModel):
    day1: DaySchedule
    day2: DaySchedule
    day3: DaySchedule
    day4: DaySchedule
    day5: DaySchedule
    day6: DaySchedule
    day7: DaySchedule

class WorkoutPlanBase(BaseModel):
    plan_name: str
    duration_weeks: int
    primary_goal: str
    weekly_schedule: Dict[str, Any] # Using Dict/Any for flexibility, or could use WeeklySchedule model if structure is rigid
    progression_guidelines: List[str]
    cardio_recommendations: List[str]

class WorkoutPlanCreate(WorkoutPlanBase):
    pass

class ProfileData(BaseModel):
    weight_kg: float
    height_cm: float
    target_weight_kg: float
    fitness_goal: str
    activity_level: str

class WorkoutPreferencesInput(BaseModel):
    experience_level: str
    days_per_week: int
    session_duration_min: int
    health_restrictions: Optional[str] = "none"

class WorkoutPlanRequestData(BaseModel):
    user_id: Optional[int] = None
    workout_preferences: WorkoutPreferencesInput
    custom_prompt: Optional[str] = None
    ignore_history: bool = False

class WorkoutPlanRequest(BaseModel):
    workout_request: WorkoutPlanRequestData

class WorkoutPlanResponse(WorkoutPlanBase):
    id: int
    user_profile_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
