from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MealPlanGenerateRequest(BaseModel):
    custom_prompt: Optional[str] = None

class NutrientDetail(BaseModel):
    p: float
    c: float
    f: float

class MealItem(BaseModel):
    meal_id: str
    label: str
    is_veg: bool
    dish_name: str
    portion_size: str
    nutrients: NutrientDetail
    alternatives: List[str]
    guidelines: List[str]
    feast_notes: Optional[List[str]] = None
    is_user_adjusted: Optional[bool] = False
    adjustment_note: Optional[str] = None
    original_nutrients: Optional[NutrientDetail] = None
    original_portion_size: Optional[str] = None

class NutrientTotals(BaseModel):
    calories: float
    protein: float
    carbs: float
    fat: float

class MealPlanResponse(BaseModel):
    user_profile_id: int
    daily_targets: Optional[NutrientTotals] = None
    daily_generated_totals: Optional[NutrientTotals] = None
    meal_plan: List[MealItem]
    verification: Optional[str] = None
    verification: Optional[str] = None
    created_at: Optional[datetime] = None