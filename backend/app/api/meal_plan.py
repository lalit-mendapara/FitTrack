from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.meal_service import generate_meal_plan, restore_original_plan 
from app.crud.meal_plan import get_current_meal_plan
from app.schemas.meal_plan import MealPlanResponse, MealPlanGenerateRequest, MealItem, NutrientDetail
from app.models.meal_plan import MealPlan
from app.models.user_profile import UserProfile
from app.models.user import User
from app.api.auth import get_current_user
import sys

# Langfuse tracing
observe = lambda *args, **kwargs: (lambda f: f)  # No-op decorator fallback
if sys.version_info < (3, 14):
    try:
        from langfuse import observe
    except ImportError:
        pass

router = APIRouter(
    prefix="/meal-plans",
    tags=["Meal Plans"]
)

from app.models.tracking import FoodLog

@router.post("/", response_model=MealPlanResponse)
@observe(name="generate_meal_plan")
def generate_meal_plan_endpoint(
    request: MealPlanGenerateRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    custom_prompt = request.custom_prompt if request else None
    print(f"Generating meal plan for: {current_user.email} with prompt: {custom_prompt}")
    try:
        # LOG PRESERVATION: Do NOT delete old logs.
        # db.query(FoodLog).filter(FoodLog.user_id == current_user.id).delete()
        # db.commit()

        meal_plan = generate_meal_plan(db, current_user.id, custom_prompt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not meal_plan:
        raise HTTPException(status_code=400, detail="Could not generate meal plan")
    
    return meal_plan

@router.post("/regenerate", response_model=MealPlanResponse)
@observe(name="regenerate_meal_plan")
def regenerate_meal_plan_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.services.meal_service import regenerate_meal_plan
    try:
        # LOG PRESERVATION: Do NOT delete old logs.
        # db.query(FoodLog).filter(FoodLog.user_id == current_user.id).delete()
        # db.commit()
        
        meal_plan = regenerate_meal_plan(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not meal_plan:
        raise HTTPException(status_code=400, detail="Could not regenerate meal plan")
        
    return meal_plan

@router.get("/current", response_model=MealPlanResponse)
def get_current_meal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meal_plan = get_current_meal_plan(db, current_user.id)
    if not meal_plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    
    return meal_plan


from pydantic import BaseModel
from typing import Optional, List

class SkipMealRequest(BaseModel):
    meal_id: str
    redistribute_to: Optional[List[str]] = None
    is_feast_day: bool = False

@router.post("/skip-meal")
def skip_meal_endpoint(
    request: SkipMealRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Feast Mode: Skip a meal.
    On feast day: redistributes calories to remaining meals.
    On banking day: just zeros the meal (extra calories banked).
    """
    from app.services.meal_service import skip_meal_and_redistribute
    
    result = skip_meal_and_redistribute(
        db, current_user.id, request.meal_id, request.redistribute_to, request.is_feast_day
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

    return result


@router.post("/reset", response_model=dict)
def reset_meal_plan_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reset meal plan to original generated state (undo adjustments).
    """
    result = restore_original_plan(db, current_user.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
