#!/usr/bin/env python3
"""
Script to check actual database values for analytics
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
        # Count total meal plans
        total_meal_plans = db.query(func.count(MealPlan.id)).scalar() or 0
        print(f'Total Meal Plans: {total_meal_plans}')
        
        # Count total workout plans
        total_workout_plans = db.query(func.count(WorkoutPlan.id)).scalar() or 0
        print(f'Total Workout Plans: {total_workout_plans}')
        
        # Count meal plans in last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        meal_plans_last_30 = db.query(func.count(MealPlan.id)).filter(
            MealPlan.created_at >= thirty_days_ago
        ).scalar() or 0
        print(f'Meal Plans (Last 30 Days): {meal_plans_last_30}')
        
        # Count workout plans in last 30 days
        workout_plans_last_30 = db.query(func.count(WorkoutPlan.id)).filter(
            WorkoutPlan.created_at >= thirty_days_ago
        ).scalar() or 0
        print(f'Workout Plans (Last 30 Days): {workout_plans_last_30}')
        
        # Sample some meal plans to check created_at
        print('\n=== Sample Meal Plans ===')
        sample_meals = db.query(MealPlan.id, MealPlan.created_at, MealPlan.user_profile_id).limit(5).all()
        for meal in sample_meals:
            print(f'  ID: {meal.id}, Created: {meal.created_at}, UserProfile: {meal.user_profile_id}')
        
        # Sample some workout plans to check created_at
        print('\n=== Sample Workout Plans ===')
        sample_workouts = db.query(WorkoutPlan.id, WorkoutPlan.created_at, WorkoutPlan.user_profile_id).limit(5).all()
        for workout in sample_workouts:
            print(f'  ID: {workout.id}, Created: {workout.created_at}, UserProfile: {workout.user_profile_id}')
        
        # Check distinct user_profile_ids
        distinct_meal_profiles = db.query(func.count(func.distinct(MealPlan.user_profile_id))).scalar() or 0
        distinct_workout_profiles = db.query(func.count(func.distinct(WorkoutPlan.user_profile_id))).scalar() or 0
        print(f'\n=== Unique Users ===')
        print(f'Distinct User Profiles with Meal Plans: {distinct_meal_profiles}')
        print(f'Distinct User Profiles with Workout Plans: {distinct_workout_profiles}')
        
        # Check if there are multiple meal plans per user
        print(f'\n=== Analysis ===')
        if total_meal_plans > 0 and distinct_meal_profiles > 0:
            avg_meals_per_user = total_meal_plans / distinct_meal_profiles
            print(f'Average Meal Plans per User: {avg_meals_per_user:.2f}')
        
        if total_workout_plans > 0 and distinct_workout_profiles > 0:
            avg_workouts_per_user = total_workout_plans / distinct_workout_profiles
            print(f'Average Workout Plans per User: {avg_workouts_per_user:.2f}')
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
