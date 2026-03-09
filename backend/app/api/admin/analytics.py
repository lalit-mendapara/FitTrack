from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
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
from typing import List, Dict, Any
from datetime import datetime, timedelta

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


class UserGrowthData(BaseModel):
    labels: List[str]
    data: List[int]


class PlanGenerationStats(BaseModel):
    total_meal_plans: int
    total_workout_plans: int
    meal_plans_last_30_days: int
    workout_plans_last_30_days: int


class AICoachUsage(BaseModel):
    total_sessions: int
    total_messages: int
    active_sessions_last_7_days: int
    avg_messages_per_session: float


class FeastModeStats(BaseModel):
    total_feasts: int
    active_feasts: int
    completed_feasts: int
    cancelled_feasts: int
    avg_banking_days: float


class UserDemographics(BaseModel):
    gender_distribution: Dict[str, int]
    age_distribution: Dict[str, int]


@router.get("/user-growth")
async def get_user_growth(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get user growth data for the last 12 months
    
    Y-axis: Number of users (cumulative count)
    X-axis: Month labels (e.g., 'Jan 2026', 'Feb 2026')
    
    This shows REAL data from the database using the created_at field.
    """
    try:
        now = datetime.now()
        labels = []
        data = []
        
        # Generate data for last 12 months
        for i in range(11, -1, -1):
            # Calculate the end of each month
            month_date = now - timedelta(days=30 * i)
            month_name = month_date.strftime("%b %Y")
            labels.append(month_name)
            
            # Calculate end of this month for the query
            if i == 0:
                # Current month - use current time
                month_end = now
            else:
                # Previous months - use end of that month
                month_end = now - timedelta(days=30 * (i - 1))
            
            # Count users created up to the end of this month
            user_count = db.query(func.count(User.id)).filter(
                User.created_at <= month_end
            ).scalar() or 0
            
            data.append(user_count)
        
        return UserGrowthData(labels=labels, data=data)
    except Exception as e:
        import traceback
        print(f"Error in user growth: {str(e)}")
        print(traceback.format_exc())
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Error fetching user growth: {str(e)}")


@router.get("/plan-generation-stats", response_model=PlanGenerationStats)
async def get_plan_generation_stats(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get plan generation statistics with REAL last 30 days data"""
    try:
        total_meal_plans = db.query(func.count(MealPlan.id)).scalar() or 0
        total_workout_plans = db.query(func.count(WorkoutPlan.id)).scalar() or 0
        
        # Calculate date 30 days ago
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # Count plans created in last 30 days using created_at field
        meal_plans_last_30_days = db.query(func.count(MealPlan.id)).filter(
            MealPlan.created_at >= thirty_days_ago
        ).scalar() or 0
        
        workout_plans_last_30_days = db.query(func.count(WorkoutPlan.id)).filter(
            WorkoutPlan.created_at >= thirty_days_ago
        ).scalar() or 0
        
        return PlanGenerationStats(
            total_meal_plans=total_meal_plans,
            total_workout_plans=total_workout_plans,
            meal_plans_last_30_days=meal_plans_last_30_days,
            workout_plans_last_30_days=workout_plans_last_30_days
        )
    except Exception as e:
        import traceback
        print(f"Error in plan generation stats: {str(e)}")
        print(traceback.format_exc())
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Error fetching plan stats: {str(e)}")


@router.get("/ai-coach-usage", response_model=AICoachUsage)
async def get_ai_coach_usage(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get AI Coach usage statistics with REAL message counts and date filters"""
    try:
        from app.models.chat import ChatHistory
        
        total_sessions = db.query(func.count(ChatSession.id)).scalar() or 0
        
        # Count REAL total messages from chat_history table
        total_messages = db.query(func.count(ChatHistory.id)).scalar() or 0
        
        # Calculate date 7 days ago
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        # Count active sessions in last 7 days using created_at field
        active_sessions_last_7_days = db.query(func.count(ChatSession.id)).filter(
            ChatSession.created_at >= seven_days_ago
        ).scalar() or 0
        
        # Calculate REAL average messages per session
        if total_sessions > 0:
            avg_messages_per_session = round(total_messages / total_sessions, 1)
        else:
            avg_messages_per_session = 0.0
        
        return AICoachUsage(
            total_sessions=total_sessions,
            total_messages=total_messages,
            active_sessions_last_7_days=active_sessions_last_7_days,
            avg_messages_per_session=avg_messages_per_session
        )
    except Exception as e:
        import traceback
        print(f"Error in AI coach usage: {str(e)}")
        print(traceback.format_exc())
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Error fetching AI coach usage: {str(e)}")


@router.get("/feast-mode-stats", response_model=FeastModeStats)
async def get_feast_mode_stats(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get Feast Mode statistics with REAL average banking days calculation"""
    try:
        total_feasts = db.query(func.count(FeastConfig.id)).scalar() or 0
        active_feasts = db.query(func.count(FeastConfig.id)).filter(
            FeastConfig.is_active == True
        ).scalar() or 0
        
        # Count by status
        completed_feasts = db.query(func.count(FeastConfig.id)).filter(
            FeastConfig.status == "COMPLETED"
        ).scalar() or 0
        
        cancelled_feasts = db.query(func.count(FeastConfig.id)).filter(
            FeastConfig.status == "CANCELLED"
        ).scalar() or 0
        
        # Calculate REAL average banking days from database
        # Banking days = days between start_date and event_date
        feasts_with_dates = db.query(
            FeastConfig.start_date,
            FeastConfig.event_date
        ).filter(
            FeastConfig.start_date.isnot(None),
            FeastConfig.event_date.isnot(None)
        ).all()
        
        if feasts_with_dates:
            total_banking_days = sum(
                (event_date - start_date).days 
                for start_date, event_date in feasts_with_dates
            )
            avg_banking_days = round(total_banking_days / len(feasts_with_dates), 1)
        else:
            avg_banking_days = 0.0
        
        return FeastModeStats(
            total_feasts=total_feasts,
            active_feasts=active_feasts,
            completed_feasts=completed_feasts,
            cancelled_feasts=cancelled_feasts,
            avg_banking_days=avg_banking_days
        )
    except Exception as e:
        import traceback
        print(f"Error in feast mode stats: {str(e)}")
        print(traceback.format_exc())
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Error fetching feast stats: {str(e)}")


@router.get("/user-demographics", response_model=UserDemographics)
async def get_user_demographics(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get user demographics data"""
    try:
        # Gender distribution
        gender_counts = db.query(
            User.gender,
            func.count(User.id)
        ).filter(
            User.gender.isnot(None)
        ).group_by(User.gender).all()
        
        gender_distribution = {gender: count for gender, count in gender_counts}
        
        # Age distribution
        age_ranges = {
            "18-25": 0,
            "26-35": 0,
            "36-45": 0,
            "46-55": 0,
            "56+": 0
        }
        
        users_with_age = db.query(User.age).filter(User.age.isnot(None)).all()
        for (age,) in users_with_age:
            if age <= 25:
                age_ranges["18-25"] += 1
            elif age <= 35:
                age_ranges["26-35"] += 1
            elif age <= 45:
                age_ranges["36-45"] += 1
            elif age <= 55:
                age_ranges["46-55"] += 1
            else:
                age_ranges["56+"] += 1
        
        return UserDemographics(
            gender_distribution=gender_distribution,
            age_distribution=age_ranges
        )
    except Exception as e:
        import traceback
        print(f"Error in user demographics: {str(e)}")
        print(traceback.format_exc())
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Error fetching demographics: {str(e)}")
