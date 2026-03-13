#!/usr/bin/env python3
"""
Script to test the fixed analytics queries
"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Load environment variables
from dotenv import load_dotenv
env_path = backend_path / ".env"
load_dotenv(env_path)

from app.database import SessionLocal
from app.models.meal_plan import MealPlan
from app.models.workout_plan import WorkoutPlan
from sqlalchemy import func
from datetime import datetime, timedelta

def main():
    db = SessionLocal()
    
    try:
        print("=== FIXED ANALYTICS QUERIES ===\n")
        
        # Count distinct users with meal plans (FIXED)
        total_meal_plans = db.query(func.count(func.distinct(MealPlan.user_profile_id))).scalar() or 0
        print(f'Total Meal Plans (Distinct Users): {total_meal_plans}')
        
        # Count total workout plans
        total_workout_plans = db.query(func.count(WorkoutPlan.id)).scalar() or 0
        print(f'Total Workout Plans: {total_workout_plans}')
        
        # Calculate date 30 days ago
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # Count distinct users who got meal plans in last 30 days (FIXED)
        meal_plans_last_30_days = db.query(func.count(func.distinct(MealPlan.user_profile_id))).filter(
            MealPlan.created_at >= thirty_days_ago
        ).scalar() or 0
        print(f'Meal Plans Last 30 Days (Distinct Users): {meal_plans_last_30_days}')
        
        # Count workout plans in last 30 days
        workout_plans_last_30_days = db.query(func.count(WorkoutPlan.id)).filter(
            WorkoutPlan.created_at >= thirty_days_ago
        ).scalar() or 0
        print(f'Workout Plans Last 30 Days: {workout_plans_last_30_days}')
        
        print("\n=== COMPARISON ===")
        print(f'OLD: Total Meal Plans = 100 (counting all meal entries)')
        print(f'NEW: Total Meal Plans = {total_meal_plans} (counting unique users)')
        print(f'\nThis correctly represents {total_meal_plans} users have meal plans.')
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
