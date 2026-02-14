from pydantic import BaseModel
from typing import Optional, List
from datetime import date

# REQUESTS
class FeastProposalRequest(BaseModel):
    event_name: str
    event_date: date
    custom_deduction: Optional[int] = None

class FeastActivateRequest(BaseModel):
    event_name: str
    event_date: date
    daily_deduction: int
    total_banked: int
    start_date: date
    workout_boost: bool = True
    custom_deduction: Optional[int] = None

class FeastUpdateRequest(BaseModel):
    daily_deduction: Optional[int] = None
    workout_boost: Optional[bool] = None

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

class FeastOverrideResponse(BaseModel):
    meal_id: str
    adjusted_calories: float
    adjusted_protein: float
    adjusted_carbs: float
    adjusted_fat: float
    adjusted_portion_size: str
    adjustment_note: Optional[str] = None
    adjustment_method: str
