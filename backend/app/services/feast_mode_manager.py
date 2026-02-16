from datetime import date, timedelta
import logging
import json
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.feast_config import FeastConfig, FeastMealOverride
from app.models.user_profile import UserProfile
from app.models.meal_plan import MealPlan
from app.models.tracking import FoodLog
from app.models.workout_plan import WorkoutPlan
from app.services import llm_service

logger = logging.getLogger(__name__)

class FeastModeManager:
    def __init__(self, db: Session):
        self.db = db

    def propose_strategy(self, user_id: int, event_date: date, event_name: str, custom_deduction: int = None):
        """
        Calculates a proposed banking strategy for a future event.
        Returns a dict with the proposal details.
        """
        today = date.today()
        days_until = (event_date - today).days
        
        if days_until <= 0:
            return {"error": "Event must be in the future"}
            
        if days_until > 14:
            return {"error": "Event is too far away (max 2 weeks)"}

        if custom_deduction and custom_deduction > 0:
            # User specified their own deduction
            daily_deduction = min(custom_deduction, 500)  # Safety cap
            daily_deduction = round(daily_deduction / 50) * 50  # Round to nearest 50
            target_bank = daily_deduction * days_until
        else:
            # Default logic: Target 800-1000 kcal buffer
            target_bank = 800
            daily_deduction = int(target_bank / days_until)
            
            # Safety Check: cap at 500 kcal/day
            if daily_deduction > 500:
                target_bank = 500 * days_until
                daily_deduction = 500
            
            # Round to nearest 50
            daily_deduction = round(daily_deduction / 50) * 50
            target_bank = daily_deduction * days_until
        
        # Get base targets for preview
        # This ensures we start from the LLM-generated baseline
        # Get base targets for preview
        # This ensures we start from the LLM-generated baseline
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        base_cals = profile.calories if profile else 2000
        
        # Calculate from active meal plan items
        meal_plans = self.db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all() if profile else []
        if meal_plans:
             calculated_cals = 0
             for m in meal_plans:
                 if m.nutrients and isinstance(m.nutrients, dict):
                     calculated_cals += m.nutrients.get("calories", 0)
             
             # If we have a valid sum, use it. Otherwise fallback to profile.
             if calculated_cals > 500: # Safety check against empty plans
                 base_cals = calculated_cals

        return {
            "event_name": event_name,
            "event_date": event_date,
            "days_remaining": days_until,
            "daily_deduction": daily_deduction,
            "total_banked": target_bank,
            "start_date": today,
            "base_calories": base_cals,
            "effective_calories": base_cals - daily_deduction
        }

    def activate(self, user_id: int, proposal: dict, workout_boost: bool = True, workout_preference: str = "standard"):
        """
        Activates Feast Mode based on a proposal.
        Snapshots current profile targets.
        workout_preference: 'standard' (Depletion), 'cardio' (Cardio Focus), 'skip' (No Workout Change)
        """
        # Deactivate any existing active config
        existing = self.get_active_config(user_id)
        if existing:
            self.cancel(user_id) # Cleanly cancel existing
        
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise ValueError("UserProfile not found")

        # Get Base Snapshots from Meal Plan (Preferred) or Profile
        base_cals = profile.calories
        base_p = profile.protein
        base_c = profile.carbs
        base_f = profile.fat
        
        meal_plans = self.db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()
        if meal_plans:
            calc_cals = 0
            calc_p = 0
            calc_c = 0
            calc_f = 0
            for m in meal_plans:
                if m.nutrients and isinstance(m.nutrients, dict):
                    calc_cals += m.nutrients.get("calories", 0)
                    calc_p += m.nutrients.get("protein", 0)
                    calc_c += m.nutrients.get("carbs", 0)
                    calc_f += m.nutrients.get("fat", 0)
            
            if calc_cals > 500:
                base_cals = calc_cals
                base_p = calc_p
                base_c = calc_c
                base_f = calc_f

        # Create Config
        new_config = FeastConfig(
            user_id=user_id,
            event_name=proposal["event_name"],
            event_date=proposal["event_date"],
            target_bank_calories=proposal["total_banked"],
            daily_deduction=proposal["daily_deduction"],
            start_date=proposal["start_date"],
            workout_boost_enabled=workout_boost and workout_preference != "skip",
            user_selected_deduction=proposal.get("custom_deduction"), 
            base_calories=base_cals,
            base_protein=base_p,
            base_carbs=base_c,
            base_fat=base_f,
            status="BANKING",
            is_active=True
        )
        
        # 1. Build & Store Feast Workout (if enabled AND not skipped)
        if workout_boost and workout_preference != "skip":
            from app.services.workout_service import build_feast_workout_from_db
            feast_workout = build_feast_workout_from_db(
                self.db, 
                user_id, 
                proposal["event_date"],
                preference=workout_preference
            )
            new_config.feast_workout_data = feast_workout

        self.db.add(new_config)
        self.db.flush() # Get ID
        
        # Generate overrides for today
        self._generate_overrides_for_date(new_config, profile, date.today())
        
        # Note: We NO LONGER patch the existing workout plan. 
        # The calendar endpoint will dynamically inject 'feast_workout_data' on the event date.

        self.db.commit()
        return new_config

    def _generate_overrides_for_date(self, config: FeastConfig, profile: UserProfile, target_date: date):
        """
        Generates FeastMealOverride entries for the given date.
        Calculates effective budget (Base - Deduction OR Base + Bonus).
        """
        # 1. Calculate Effective Target
        effective_targets = self.get_effective_targets(config.user_id, target_date)
        if not effective_targets:
            return # Should not happen if config is active
            
        eff_calories = effective_targets["calories"]
        
        # 2. Get Base Meal Plan
        base_plan = self.db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()
        if not base_plan:
            return

        # 3. Check Completed Meals
        start_of_day = target_date
        completed_logs = self.db.query(FoodLog).filter(
            FoodLog.user_id == config.user_id, 
            FoodLog.date == target_date
        ).all()
        completed_meal_ids = {l.meal_type.lower() for l in completed_logs}
        
        # 4. Filter Remaining Items
        remaining_items = [m for m in base_plan if m.meal_id.lower() not in completed_meal_ids]
        
        # Calculate consumed
        consumed_cals = 0
        for m in base_plan:
            if m.meal_id.lower() in completed_meal_ids:
                consumed_cals += m.nutrients.get('calories', 0) if m.nutrients else 0
                
        remaining_budget = eff_calories - consumed_cals
        
        # 5. Generate Overrides
        overrides = []
        try:
            # Try LLM first
            try:
                overrides = self._generate_overrides_via_llm(config, remaining_items, remaining_budget, target_date)
            except Exception as e:
                logger.error(f"LLM Override Gen failed: {e}. Fallback to ratio.")
                overrides = self._generate_overrides_via_ratio(config, remaining_items, remaining_budget, target_date)
        except Exception as heavy_fail:
             logger.error(f"CRITICAL: Even fallback ratio failed: {heavy_fail}")
             overrides = [] # Proceed without overrides rather than crashing
            
        # 6. Save Overrides
        for ov in overrides:
            self.db.merge(ov) # Upsert
            
        self.db.flush()

    def _generate_overrides_via_llm(self, config: FeastConfig, remaining_items: list[MealPlan], budget: float, target_date: date):
        """
        Uses LLM to smartly adjust meals to fit budget.
        Returns list of FeastMealOverride objects.
        """
        if not remaining_items:
            return []

        # Prepare context for LLM
        current_planned = sum(m.nutrients.get('calories', 0) for m in remaining_items)
        diff = budget - current_planned
        
        if abs(diff) < 20: 
            return [] # No adjustment needed
            
        direction = "REDUCE" if diff < 0 else "INCREASE"
        abs_diff = abs(round(diff))
        
        phase = "FEAST_DAY" if target_date == config.event_date else "BANKING"
        
        items_data = []
        for m in remaining_items:
            nuts = m.nutrients or {}
            items_data.append({
                "meal_id": m.meal_id,
                "dish_name": m.dish_name,
                "portion_size": m.portion_size,
                "calories": nuts.get('calories', 0),
                "protein": nuts.get('protein', 0),
                "carbs": nuts.get('carbs', 0),
                "fat": nuts.get('fat', 0)
            })
            
        from app.utils.llm_prompts.feast_prompts import FEAST_ADJUSTMENT_SYSTEM_PROMPT
        
        system_prompt = FEAST_ADJUSTMENT_SYSTEM_PROMPT
        user_prompt = f"""Event: {config.event_name} ({phase})
Current remaining meals:
{json.dumps(items_data, indent=2)}

TASK: {direction} total calories by {abs_diff} kcal.
Current total: {current_planned:.0f} kcal -> Target: {budget:.0f} kcal.

Adjust portion_size, protein, carbs, fat.
Return ALL meals.
"""
        response = llm_service.call_llm_json(
            system_prompt=system_prompt, 
            user_prompt=user_prompt,
            temperature=0.1
        )
        
        if not response or "adjusted_meals" not in response:
            raise ValueError("Invalid LLM response")
            
        results = []
        meal_map = {m.meal_id.lower(): m for m in remaining_items}
        
        for adj in response["adjusted_meals"]:
            mid = adj.get("meal_id", "").lower()
            if mid not in meal_map: continue
            
            # Map back to Override model
            override = FeastMealOverride(
                feast_config_id=config.id,
                user_id=config.user_id,
                override_date=target_date,
                meal_id=mid,
                adjusted_calories=float(adj.get("calories", 0) or adj.get("cal", 0)),
                adjusted_protein=float(adj.get("protein", 0) or adj.get("p", 0)),
                adjusted_carbs=float(adj.get("carbs", 0) or adj.get("c", 0)),
                adjusted_fat=float(adj.get("fat", 0) or adj.get("f", 0)),
                adjusted_portion_size=adj.get("portion_size", ""),
                adjustment_note=adj.get("note", ""),
                adjustment_method="llm"
            )
            results.append(override)
            
        return results

    def _generate_overrides_via_ratio(self, config: FeastConfig, remaining_items: list[MealPlan], budget: float, target_date: date):
        """
        Fallback method using math ratios. Safe against None values.
        """
        current_planned = 0
        for m in remaining_items:
            if m.nutrients and isinstance(m.nutrients, dict):
                 current_planned += m.nutrients.get('calories', 0)
                 
        if current_planned == 0: return []
        
        ratio = budget / current_planned
        ratio = max(0.5, min(ratio, 2.0)) # Safety Caps
        
        results = []
        for m in remaining_items:
            nuts = m.nutrients or {}
            orig_cal = nuts.get('calories', 0)
            
            # Scale nutrients
            new_cal = orig_cal * ratio
            new_p = nuts.get('protein', 0) * ratio
            new_c = nuts.get('carbs', 0) * ratio
            new_f = nuts.get('fat', 0) * ratio
            
            # Scale portion string
            import re
            new_portion = re.sub(r'\b(\d+(\.\d+)?)\b', 
                lambda match: f"{float(match.group(1)) * ratio:.0f}", 
                m.portion_size
            )
            
            override = FeastMealOverride(
                feast_config_id=config.id,
                user_id=config.user_id,
                override_date=target_date,
                meal_id=m.meal_id.lower(),
                adjusted_calories=new_cal,
                adjusted_protein=new_p,
                adjusted_carbs=new_c,
                adjusted_fat=new_f,
                adjusted_portion_size=new_portion,
                adjustment_note=f"Auto-scaled {'down' if ratio < 1 else 'up'} (Ratio {ratio:.2f})",
                adjustment_method="ratio"
            )
            results.append(override)
            
        return results

    def get_active_config(self, user_id: int, current_date: date = None):
        if not current_date:
            current_date = date.today()
            
        return self.db.query(FeastConfig).filter(
            FeastConfig.user_id == user_id,
            FeastConfig.is_active == True,
            FeastConfig.event_date >= current_date # Not expired
        ).first()

    def get_effective_targets(self, user_id: int, current_date: date):
        """
        Returns {calories, protein, carbs, fat} with banking/feast logic applied.
        """
        config = self.get_active_config(user_id, current_date)
        
        # Determine Base Targets
        # Ideally we use the SNAPSHOT from config to prevent drift, 
        # but if no config, we fallback to current profile.
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        base = {
            "calories": profile.calories if profile else 2000,
            "protein": profile.protein if profile else 150,
            "carbs": profile.carbs if profile else 200,
            "fat": profile.fat if profile else 60
        }
        
        if not config:
            return base
            
        effective = base.copy()
        # Use snapshot if available (consistency) - OPTIONAL but recommended
        if config.base_calories:
             effective = {
                "calories": config.base_calories,
                "protein": config.base_protein,
                "carbs": config.base_carbs,
                "fat": config.base_fat
            }
        
        # Logic from social_event_service
        if config.start_date <= current_date < config.event_date:
            # Banking Phase
            deduction = config.daily_deduction
            effective['calories'] -= deduction
            
            # 60% Carbs, 40% Fat reduction
            effective['carbs'] -= (deduction * 0.6 / 4)
            effective['fat'] -= (deduction * 0.4 / 9)
            
        elif current_date == config.event_date:
            # Feast Phase
            bonus = config.target_bank_calories
            effective['calories'] += bonus
            effective['carbs'] += (bonus * 0.5 / 4)
            effective['fat'] += (bonus * 0.5 / 9)
            
        return effective

    def get_overrides_for_date(self, user_id: int, target_date: date):
        config = self.get_active_config(user_id, target_date)
        if not config: return {}
        
        overrides = self.db.query(FeastMealOverride).filter(
            FeastMealOverride.feast_config_id == config.id,
            FeastMealOverride.override_date == target_date
        ).all()
        
        return {ov.meal_id.lower(): ov for ov in overrides}

    def cancel(self, user_id: int):
        config = self.get_active_config(user_id)
        if not config:
            return {"message": "No active feast mode found"}
            
        config.is_active = False
        config.status = "CANCELLED"
        
        # Note: No need to call restore_workout_plan() anymore.
        # Since we stopped patching the weekly_schedule, the original schedule
        # automatically shows up when is_active becomes False.
            
        self.db.commit()
        return {"message": "Feast Mode cancelled", "restored_calories": config.base_calories}
        
    def auto_complete_expired(self, user_id: int):
        # Find active events in the past
        expired = self.db.query(FeastConfig).filter(
            FeastConfig.user_id == user_id,
            FeastConfig.is_active == True,
            FeastConfig.event_date < date.today()
        ).all()
        
        if not expired: return False
        
        for ex in expired:
            ex.is_active = False
            ex.status = "COMPLETED"
            
        self.db.commit()
        return True

    def inject_feast_workout_into_plan(self, user_id: int, workout_plan_schedule: dict) -> dict:
        """
        Injects the Feast Mode workout into the provided weekly_schedule dictionary 
        if the event date falls on one of the schedule days.
        """
        config = self.get_active_config(user_id)
        if not config or not config.feast_workout_data:
            return workout_plan_schedule

        # Check if event date matches any day in the schedule
        event_day_name = config.event_date.strftime("%A") # e.g. "Friday"
        
        updated_schedule = workout_plan_schedule.copy()
        
        for key, day_data in updated_schedule.items():
            if day_data.get("day_name") == event_day_name:
                # Injection!
                feast_data = config.feast_workout_data
                if isinstance(feast_data, dict):
                    # We merge/replace to preserve structure but update content
                    day_data["workout_name"] = feast_data.get("workout_name", "Feast Mode Workout")
                    day_data["focus"] = feast_data.get("focus", "Glycogen Depletion")
                    day_data["exercises"] = feast_data.get("exercises", [])
                    day_data["cardio_exercises"] = feast_data.get("cardio_exercises", [])
                    day_data["is_rest"] = False
                    day_data["notes"] = "Special workout for your upcoming Feast!"
                
        return updated_schedule

    def update_mid_day(self, user_id: int, new_deduction: int = None, workout_boost: bool = None):
        config = self.get_active_config(user_id)
        if not config:
            return {"error": "No active feast mode"}
            
        if new_deduction is not None:
            # Recalculate
            days_remaining = (config.event_date - date.today()).days
            if days_remaining <= 0: return {"error": "Cannot change deduction on/after feast day"}
            
            config.daily_deduction = new_deduction
            config.target_bank_calories = new_deduction * days_remaining
            
            # Regenerate Today's Overrides
            # Delete old overrides for today
            self.db.query(FeastMealOverride).filter(
                FeastMealOverride.feast_config_id == config.id,
                FeastMealOverride.override_date == date.today()
            ).delete()
            
            # Check profile
            profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            self._generate_overrides_for_date(config, profile, date.today())

        if workout_boost is not None:
            config.workout_boost_enabled = workout_boost
            # Patch or Restore workout logic if needed
            # ...
            
        self.db.commit()
        return {"message": "Feast Mode updated"}

    def get_feast_context_for_ai(self, user_id: int):
        config = self.get_active_config(user_id)
        if not config: return None
        
        today = date.today()
        days_remaining = (config.event_date - today).days
        phase = "FEAST_DAY" if days_remaining == 0 else "BANKING"
        
        overrides = self.get_overrides_for_date(user_id, today)
        override_summary = [f"{k}: {v.adjusted_calories:.0f}kcal ({v.adjustment_note})" for k,v in overrides.items()]
        
        return {
            "event_name": config.event_name,
            "event_date": config.event_date.isoformat(),
            "phase": phase,
            "days_remaining": days_remaining,
            "daily_deduction": config.daily_deduction,
            "total_bank_target": config.target_bank_calories,
            "effective_calories": config.base_calories - config.daily_deduction if phase == "BANKING" else config.base_calories + config.target_bank_calories,
            "workout_boost": config.workout_boost_enabled,
            "todays_overrides": override_summary
        }

    def get_deactivation_preview(self, user_id: int):
        """
        Returns what will happen if Feast Mode is cancelled now.
        """
        config = self.get_active_config(user_id)
        if not config:
            return {"error": "No active feast mode"}
            
        today = date.today()
        
        # Current State
        current_effective = self.get_effective_targets(user_id, today)
        
        # Forecasted State (Restored)
        # We use the snapshot base_calories
        restored_calories = config.base_calories
        
        # Workout Impact
        workout_msg = "No changes to workout schedule."
        if config.workout_boost_enabled:
             workout_msg = f"The Depletion Workout on {config.event_date} will be removed."
             
        days_active = (today - config.start_date).days
        total_banked_so_far = max(0, days_active * config.daily_deduction)
        
        return {
            "current_daily_calories": current_effective["calories"],
            "restored_daily_calories": restored_calories,
            "banked_calories_lost": total_banked_so_far,
            "workout_status": workout_msg,
            "event_name": config.event_name
        }
