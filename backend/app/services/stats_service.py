from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.models.user_profile import UserProfile
from app.models.meal_plan import MealPlan
from app.models.workout_plan import WorkoutPlan
from app.models.workout_preferences import WorkoutPreferences
from app.models.food_item import FoodItem
from app.models.exercise import Exercise
from app.models.tracking import FoodLog, WorkoutLog
from sqlalchemy import func
from datetime import datetime, date, timedelta

class StatsService:
    """
    The Auditor: Fetches user stats, targets, and today's planned activities.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch user profile and targets."""
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = self.db.execute(stmt).scalar_one_or_none()
        
        if not result:
            return None
            
        # Check for active Social Event (Feast Mode)
        try:
            from app.services.social_event_service import get_active_event
            social_event = get_active_event(self.db, user_id)
            
            calorie_target = result.calories
            if social_event and social_event.is_active:
                today = date.today()
                # Apply deduction if today is a banking day (Start Date <= Today < Event Date)
                if social_event.start_date <= today < social_event.event_date:
                    calorie_target -= social_event.daily_deduction
                # Apply boost if today is the event day
                elif today == social_event.event_date:
                    calorie_target += social_event.target_bank_calories
        except Exception as e:
            print(f"Error checking social event deduction: {e}")
            calorie_target = result.calories

        return {
            "weight": result.weight,
            "height": result.height,
            "weight_goal": result.weight_goal,
            "fitness_goal": result.fitness_goal,
            "activity_level": result.activity_level,
            "caloric_target": calorie_target,
            "protein_target": result.protein,
            "carb_target": result.carbs,
            "fat_target": result.fat,
            "diet_type": result.diet_type,
            "country": result.country
        }

    def get_todays_plan(self, user_id: int) -> Dict[str, Any]:
        """
        Fetch today's meal plan and workout scheduled.
        """
        # Helper to get day name (e.g., "Monday")
        today_name = datetime.now().strftime("%A")
        
        # 1. Fetch User Profile ID
        stmt_profile = select(UserProfile.id).where(UserProfile.user_id == user_id)
        profile_id = self.db.execute(stmt_profile).scalar_one_or_none()
        
        if not profile_id:
            return {"meals": [], "workout": None, "day": today_name}

        # 2. Fetch Meals (Assuming MealPlan rows constitute the daily plan)
        # Note: If MealPlan has day-specific logic, it should be filtered here.
        # Based on the model, MealPlan seems to be a list of meals for the "current plan".
        stmt_meals = select(MealPlan).where(MealPlan.user_profile_id == profile_id)
        meal_records = self.db.execute(stmt_meals).scalars().all()
        
        meals_data = []
        for meal in meal_records:
            # Handle key variations (p vs protein) and missing calories
            nutrients = meal.nutrients or {}
            
            protein = nutrients.get("protein") or nutrients.get("p", 0)
            calories = nutrients.get("calories")
            
            # If calories are missing/0, estimate them
            if not calories:
                p = float(protein)
                c = float(nutrients.get("carbs") or nutrients.get("c", 0))
                f = float(nutrients.get("fat") or nutrients.get("f", 0))
                calories = (p * 4) + (c * 4) + (f * 9)

            meals_data.append({
                "meal": meal.meal_id, # e.g. "breakfast"
                "dish": meal.dish_name,
                "portion_size": meal.portion_size,
                "guidelines": meal.guidelines,
                "alternatives": meal.alternatives,
                "calories": int(calories),
                "protein": int(protein),
                "carbs": int(nutrients.get("carbs") or nutrients.get("c", 0)),
                "fat": int(nutrients.get("fat") or nutrients.get("f", 0)),
                "nutrients": nutrients # Pass full dict safely if needed
            })

        # 3. Fetch Workout for Today
        stmt_workout = select(WorkoutPlan).where(WorkoutPlan.user_profile_id == profile_id)
        workout_plan = self.db.execute(stmt_workout).scalar_one_or_none()
        
        todays_workout = None
        if workout_plan and workout_plan.weekly_schedule:
            # weekly_schedule is likely a dict keyed by day name
            # e.g. {"Monday": {...}, "Tuesday": {...}}
            schedule = workout_plan.weekly_schedule
            if isinstance(schedule, dict):
                # Try exact match or partial match if keys differ
                todays_workout = schedule.get(today_name)
                
                # Fallback if keys are lowercase
                if not todays_workout:
                     todays_workout = schedule.get(today_name.lower())

        return {
            "meals": meals_data,
            "workout": todays_workout,
            "day": today_name
        }

    def search_food_by_name(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Exact/Partial Match search in SQL (The Auditor - Fallback).
        """
        # Search for name containing query (case-insensitive)
        stmt = select(FoodItem).where(FoodItem.name.ilike(f"%{query}%")).limit(limit)
        results = self.db.execute(stmt).scalars().all()
        
        return [{
            "name": item.name,
            "protein": float(item.protein_g),
            "calories": float(item.calories_kcal),
            "diet_type": item.diet_type,
            "source": "SQL"
        } for item in results]

    def search_exercise_by_name(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Exact/Partial Match search in SQL (The Auditor - Fallback).
        """
        stmt = select(Exercise).where(Exercise.name.ilike(f"%{query}%")).limit(limit)
        results = self.db.execute(stmt).scalars().all()
        
        return [{
            "name": item.name,
            "category": item.category,
            "muscle_group": item.primary_muscle,
            "difficulty": item.difficulty,
            "source": "SQL"
        } for item in results]

    def get_full_user_context(self, user_id: int) -> Dict[str, Any]:
        """
        Fetch EVERYTHING known about the user for the "Omniscient" context.
        """
        # 1. Profile
        stmt_profile = select(UserProfile).where(UserProfile.user_id == user_id)
        profile = self.db.execute(stmt_profile).scalar_one_or_none()
        
        if not profile:
            return {}

        # 2. Daily Diet (Assuming one plan for all days for now)
        # Fetch all meal items linked to profile
        stmt_meals = select(MealPlan).where(MealPlan.user_profile_id == profile.id)
        meal_records = self.db.execute(stmt_meals).scalars().all()
        
        diet_plan = []
        for m in meal_records:
            diet_plan.append({
                "meal": m.meal_id,
                "dish": m.dish_name,
                "calories": float(m.nutrients.get('calories') or 0),
                "protein": float(m.nutrients.get('protein') or m.nutrients.get('p') or 0),
                "carbs": float(m.nutrients.get('carbs') or m.nutrients.get('c') or 0),
                "fat": float(m.nutrients.get('fat') or m.nutrients.get('f') or 0),
                "is_veg": m.is_veg,
                "portion_size": m.portion_size,
                "guidelines": m.guidelines,
                "alternatives": m.alternatives,
                "ingredients": m.nutrients.get('ingredients', [])
            })

        # 3. Full Workout Schedule
        stmt_workout = select(WorkoutPlan).where(WorkoutPlan.user_profile_id == profile.id)
        wp = self.db.execute(stmt_workout).scalar_one_or_none()
        
        workout_context = {
            "plan_name": wp.plan_name if wp else None,
            "goal": wp.primary_goal if wp else None,
            "schedule": wp.weekly_schedule if wp else {}
        }

        # 4. Workout Preferences
        stmt_prefs = select(WorkoutPreferences).where(WorkoutPreferences.user_profile_id == profile.id)
        prefs = self.db.execute(stmt_prefs).scalar_one_or_none()
        
        prefs_context = {
            "level": prefs.experience_level if prefs else "intermediate",
            "days_per_week": prefs.days_per_week if prefs else 3,
            "duration": prefs.session_duration_min if prefs else 45,
            "health_issues": prefs.health_restrictions if prefs else "None"
        }

        # Structure for the AI
        return {
            "profile": {
                "weight": profile.weight,
                "weight_goal": profile.weight_goal,
                "height": profile.height,
                "goal": profile.fitness_goal,
                "diet_type": profile.diet_type,
                "country": profile.country,
                "name": getattr(profile.user, 'name', 'User') if profile.user else 'User',
                "age": getattr(profile.user, 'age', 25) if profile.user else 25,
                "gender": getattr(profile.user, 'gender', 'male') if profile.user else 'male',
                "targets": {
                    "calories": profile.calories,
                    "protein": profile.protein,
                    "carbs": profile.carbs,
                    "fat": profile.fat
                }
            },
            "diet_plan": diet_plan,
            "workout_plan": workout_context,
            "preferences": prefs_context,
            "progress": self.get_user_progress(user_id)
        }

    def cleanup_old_logs(self, user_id: int):
        """
        Maintenance: Remove workout logs older than 7 days.
        """
        cutoff_date = date.today() - timedelta(days=7)
        try:
            # Note: SQLAlchemy delete usage
            self.db.query(WorkoutLog).filter(
                WorkoutLog.user_id == user_id,
                WorkoutLog.date < cutoff_date
            ).delete()
            self.db.commit()
        except Exception as e:
            print(f"[StatsService] Cleanup failed: {e}")
            self.db.rollback()

    def get_user_progress(self, user_id: int) -> Dict[str, Any]:
        """
        Fetch actual progress from logs (The Auditor - Tracking).
        Also triggers cleanup of old logs.
        """
        # Trigger Maintenance
        self.cleanup_old_logs(user_id)

        today = date.today()
        
        # 1. Today's Nutrition
        stmt_food = select(
            func.sum(FoodLog.calories).label("calories"),
            func.sum(FoodLog.protein).label("protein"),
            func.sum(FoodLog.carbs).label("carbs"),
            func.sum(FoodLog.fat).label("fat")
        ).where(FoodLog.user_id == user_id, FoodLog.date == today)
        
        nutrition = self.db.execute(stmt_food).one()
        
        # 2. Workouts (Last 7 Days)
        last_week = today - timedelta(days=7)
        stmt_workouts = select(func.count(WorkoutLog.id)).where(
            WorkoutLog.user_id == user_id, 
            WorkoutLog.date >= last_week
        )
        workout_count = self.db.execute(stmt_workouts).scalar() or 0

        # 3. Completed Exercises Today (For Chatbot Awareness)
        stmt_today_workouts = select(WorkoutLog.exercise_name).where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.date == today
        )
        completed_exercises = self.db.execute(stmt_today_workouts).scalars().all()

        # 4. Calorie Burn Stats (Real data)
        stmt_burn_today = select(func.sum(WorkoutLog.calories_burned)).where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.date == today
        )
        burn_today = self.db.execute(stmt_burn_today).scalar() or 0

        stmt_burn_week = select(func.sum(WorkoutLog.calories_burned)).where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.date >= last_week
        )
        burn_week = self.db.execute(stmt_burn_week).scalar() or 0
        
        # 5. Latest Workout (for context when today is empty)
        stmt_latest = select(WorkoutLog).where(
            WorkoutLog.user_id == user_id
        ).order_by(WorkoutLog.date.desc()).limit(1)
        latest_log = self.db.execute(stmt_latest).scalar_one_or_none()
        
        latest_workout_info = None
        if latest_log:
            latest_workout_info = {
                "date": latest_log.date.isoformat(), 
                "calories": float(latest_log.calories_burned),
                "exercise": latest_log.exercise_name
            }

        # 6. Previous Workout (Strictly before today, regardless of today's logs)
        stmt_previous = select(WorkoutLog).where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.date < today
        ).order_by(WorkoutLog.date.desc()).limit(1)
        prev_log = self.db.execute(stmt_previous).scalar_one_or_none()

        previous_workout_info = None
        if prev_log:
            previous_workout_info = {
                "date": prev_log.date.isoformat(),
                "calories": float(prev_log.calories_burned),
                "exercise": prev_log.exercise_name
            }

        return {
            "calories_eaten": float(nutrition.calories or 0),
            "protein_eaten": float(nutrition.protein or 0),
            "carbs_eaten": float(nutrition.carbs or 0),
            "fat_eaten": float(nutrition.fat or 0),
            "workouts_last_7_days": workout_count,
            "completed_exercises": list(completed_exercises),
            "calories_burned_today": float(burn_today),
            "calories_burned_last_7_days": float(burn_week),
            "latest_workout": latest_workout_info,
            "previous_workout": previous_workout_info
        }

    def get_suggested_exercises(self, muscle_group: str, exclude_names: List[str] = [], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch valid exercises from DB matching the muscle group, excluding those already planned.
        """
        if not muscle_group or muscle_group.lower() == "rest":
            return []

        # clean exclusion list
        exclude_norm = [n.lower().strip() for n in exclude_names]
        
        # Fuzzy match muscle group (e.g., "Chest & Triceps" -> matches "Chest")
        # We'll try to find items where primary_muscle is contained in the focus string OR vice versa
        # But SQL ILIKE is easier: if primary_muscle is in the focus string.
        
        # Actually, simpler approach:
        # If focus is "Chest & Triceps", we search for Exercise.primary_muscle ILIKE "%Chest%" OR "%Triceps%"
        # Let's split muscle_group by " & " or similar
        keywords = [k.strip() for k in muscle_group.replace("&", ",").split(",") if k.strip()]
        
        if not keywords:
            return []

        # Dynamic OR filter
        conditions = [Exercise.primary_muscle.ilike(f"%{k}%") for k in keywords]
        from sqlalchemy import or_
        
        stmt = select(Exercise).where(
            or_(*conditions),
            Exercise.difficulty.in_(["Beginner", "Intermediate"]) # Safety default
        ).limit(20) # Fetch more, then filter python side for exact duplicates if needed
        
        results = self.db.execute(stmt).scalars().all()
        
        suggestions = []
        for ex in results:
            if ex.name.lower().strip() not in exclude_norm:
                suggestions.append({
                    "name": ex.name,
                    "difficulty": ex.difficulty,
                    "muscle": ex.primary_muscle,
                    "benefits": "Good for " + ex.primary_muscle
                })
                if len(suggestions) >= limit:
                    break
        
        return suggestions
