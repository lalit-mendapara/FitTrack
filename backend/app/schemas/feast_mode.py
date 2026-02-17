from pydantic import BaseModel
from typing import Optional, List
from datetime import date

# REQUESTS
class FeastProposalRequest(BaseModel):
    event_name: str
    event_date: date
    custom_deduction: Optional[int] = None
    selected_meals: Optional[List[str]] = None

class FeastActivateRequest(BaseModel):
    event_name: str
    event_date: date
    daily_deduction: int
    total_banked: int
    start_date: date
    workout_boost: bool = True
    workout_preference: str = "standard"  # standard, cardio, skip
    custom_deduction: Optional[int] = None
    selected_meals: Optional[List[str]] = None

class FeastUpdateRequest(BaseModel):
    daily_deduction: Optional[int] = None
    workout_boost: Optional[bool] = None

class FeastPreCheckRequest(BaseModel):
    start_date: date
    daily_deduction: int
    base_calories: Optional[float] = None

class FeastPreCheckResponse(BaseModel):
    warning: bool
    message: Optional[str] = None
    calories_consumed: float
    remaining_after_deduction: float
    safe_minimum: float

class FeastDeactivationPreviewResponse(BaseModel):
    current_daily_calories: float
    restored_daily_calories: float
    banked_calories_lost: int
    workout_status: str
    event_name: str
    original_diet_snapshot: Optional[dict] = None
    meal_breakdown: Optional[dict] = None

# RESPONSES
class FeastStatusResponse(BaseModel):
    event_name: str
    event_date: date
    status: str
    daily_deduction: int
    target_bank_calories: int
    days_remaining: int
    start_date: date
    base_calories: float
    effective_calories: float
    workout_boost_enabled: bool
    selected_meals: Optional[List[str]] = None
    original_diet_snapshot: Optional[dict] = None

class FeastOverrideResponse(BaseModel):
    meal_id: str
    adjusted_calories: float
    adjusted_protein: float
    adjusted_carbs: float
    adjusted_fat: float
    adjusted_portion_size: str
    adjustment_note: Optional[str] = None
    adjustment_method: str
