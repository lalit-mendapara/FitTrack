from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.admin import Admin
from app.models.user import User
from app.models.food_item import FoodItem
from app.models.exercise import Exercise
from app.models.feast_config import FeastConfig
from app.models.meal_plan import MealPlan
from app.models.workout_plan import WorkoutPlan
from app.models.chat import ChatSession
from app.utils.admin_auth import get_current_admin
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin/analytics", tags=["Admin - Analytics"])

class DashboardStats(BaseModel):
    total_users: int
    total_foods: int
    total_exercises: int
    active_feasts: int
    total_meal_plans: int
    total_workout_plans: int
    total_chat_sessions: int

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get aggregated statistics for admin dashboard"""
    try:
        # Count users
        total_users = db.query(func.count(User.id)).scalar() or 0
        
        # Count food items
        total_foods = db.query(func.count(FoodItem.fdc_id)).scalar() or 0
        
        # Count exercises
        total_exercises = db.query(func.count(Exercise.id)).scalar() or 0
        
        # Count active feasts
        active_feasts = db.query(func.count(FeastConfig.id)).filter(
            FeastConfig.is_active == True
        ).scalar() or 0
        
        # Count meal plans
        total_meal_plans = db.query(func.count(MealPlan.id)).scalar() or 0
        
        # Count workout plans
        total_workout_plans = db.query(func.count(WorkoutPlan.id)).scalar() or 0
        
        # Count chat sessions
        total_chat_sessions = db.query(func.count(ChatSession.id)).scalar() or 0
        
        return DashboardStats(
            total_users=total_users,
            total_foods=total_foods,
            total_exercises=total_exercises,
            active_feasts=active_feasts,
            total_meal_plans=total_meal_plans,
            total_workout_plans=total_workout_plans,
            total_chat_sessions=total_chat_sessions
        )
    except Exception as e:
        import traceback
        print(f"Error in dashboard stats: {str(e)}")
        print(traceback.format_exc())
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
