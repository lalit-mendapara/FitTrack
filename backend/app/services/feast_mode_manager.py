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

    def propose_strategy(self, user_id: int, event_date: date, event_name: str, custom_deduction: int = None, selected_meals: list = None):
        """
        Calculates a proposed banking strategy for a future event.
        Returns a dict with the proposal details.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"FEAST MODE: PROPOSE STRATEGY")
        logger.info(f"  User ID: {user_id}")
        logger.info(f"  Event: {event_name} on {event_date}")
        logger.info(f"  Custom Deduction: {custom_deduction}")
        logger.info(f"  Selected Meals: {selected_meals}")
        logger.info(f"{'='*60}")

        today = date.today()
        days_until = (event_date - today).days
        
        if days_until <= 0:
            return {"error": "Event must be in the future"}
            
        if days_until > 14:
            return {"error": "Event is too far away (max 2 weeks)"}

        # Calculate base info first to distribute deduction correctly
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        base_cals = profile.calories if profile else 2000
        
        # Calculate per-meal map
        meal_plans = self.db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all() if profile else []
        meal_calorie_map = {}
        calculated_cals = 0
        
        if meal_plans:
             for m in meal_plans:
                 nuts = m.nutrients or {}
                 p = nuts.get('p', nuts.get('protein', 0))
                 c = nuts.get('c', nuts.get('carbs', 0))
                 f = nuts.get('f', nuts.get('fat', 0))
                 cals = (p * 4) + (c * 4) + (f * 9)
                 calculated_cals += cals
                 meal_calorie_map[m.meal_id.lower()] = cals
             
             if calculated_cals > 500:
                 base_cals = calculated_cals

        if custom_deduction and custom_deduction > 0:
            # User specified their own deduction
            daily_deduction = min(custom_deduction, 400)  # Safety cap 400
            daily_deduction = round(daily_deduction / 50) * 50
            target_bank = daily_deduction * days_until
        else:
            # Default logic: Target 800-1000 kcal buffer
            target_bank = 800
            daily_deduction = int(target_bank / days_until)
            
            # Safety Check: cap at 400 kcal/day
            if daily_deduction > 400:
                target_bank = 400 * days_until
                daily_deduction = 400
            
            # Round to nearest 50
            daily_deduction = round(daily_deduction / 50) * 50
            target_bank = daily_deduction * days_until
        
        # Calculate deduction per meal
        affected_meals = selected_meals if selected_meals else ["breakfast", "lunch", "dinner", "snacks"]
        affected_meals = [m.lower() for m in affected_meals]
        
        # Filter map to existing meals
        # Filter map to existing meals
        valid_affected = [m for m in affected_meals if m in meal_calorie_map]
        if not valid_affected and meal_plans and not selected_meals:
             # Fallback if selected meals don't exist in plan AND user didn't explicitly select specific ones
             # If user explicitly selected "snacks" and "dinner" but "snacks" isn't in map (maybe 0 cals?), we should respecting the explicit choice 
             # but we can't deduct from nothing.
             
             # If user didn't select any (defaulting to all), and we found none matching (weird), fallback to all available keys.
             valid_affected = list(meal_calorie_map.keys())

        logger.info(f"FEAST MODE PROPOSAL: Valid affected meals: {valid_affected} (from desired: {affected_meals})")
        logger.info(f"FEAST MODE PROPOSAL: Meal calorie map: {meal_calorie_map}")
        
        deduction_per_meal = 0
        if valid_affected:
            deduction_per_meal = daily_deduction / len(valid_affected)

        proposal = {
            "event_name": event_name,
            "event_date": event_date,
            "days_remaining": days_until,
            "daily_deduction": daily_deduction,
            "total_banked": target_bank,
            "start_date": today,
            "base_calories": base_cals,
            "effective_calories": base_cals - daily_deduction,
            "selected_meals": selected_meals,
            "meal_calorie_map": meal_calorie_map,
            "deduction_per_meal": deduction_per_meal
        }
        logger.info(f"FEAST MODE PROPOSAL RESULT: {proposal}")
        return proposal



    def activate(self, user_id: int, proposal: dict, workout_boost: bool = True, workout_preference: str = "standard"):
        """
        Activates Feast Mode based on a proposal.
        Snapshots current profile targets.
        workout_preference: 'standard' (Depletion), 'cardio' (Cardio Focus), 'skip' (No Workout Change)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"FEAST MODE: ACTIVATE")
        logger.info(f"  User ID: {user_id}")
        logger.info(f"  Event: {proposal.get('event_name')} on {proposal.get('event_date')}")
        logger.info(f"  Daily Deduction: {proposal.get('daily_deduction')} kcal")
        logger.info(f"  Total Bank Target: {proposal.get('total_banked')} kcal")
        logger.info(f"  Selected Meals: {proposal.get('selected_meals')}")
        logger.info(f"  Workout Boost: {workout_boost}, Preference: {workout_preference}")
        logger.info(f"{'='*60}")
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
        
        # Prepare Snapshot
        diet_snapshot = {
            "total": base_cals,
            "meals": {}
        }
        
        meal_plans = self.db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()
        if meal_plans:
            calc_cals = 0
            calc_p = 0
            calc_c = 0
            calc_f = 0
            for m in meal_plans:
                nuts = m.nutrients or {}
                p = nuts.get('p', nuts.get('protein', 0))
                c = nuts.get('c', nuts.get('carbs', 0))
                f = nuts.get('f', nuts.get('fat', 0))
                cals = (p * 4) + (c * 4) + (f * 9)
                
                diet_snapshot["meals"][m.meal_id.lower()] = cals
                
                calc_cals += cals
                calc_p += p
                calc_c += c
                calc_f += f
            
            if calc_cals > 500:
                base_cals = calc_cals
                base_p = calc_p
                base_c = calc_c
                base_f = calc_f
                diet_snapshot["total"] = base_cals

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
            selected_meals=proposal.get("selected_meals"),
            original_diet_snapshot=diet_snapshot,
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
        logger.info(f"\n{'='*60}")
        logger.info(f"FEAST MODE: GENERATE OVERRIDES FOR DATE {target_date}")
        logger.info(f"  Config ID: {config.id}, User ID: {config.user_id}")
        logger.info(f"  Daily Deduction: {config.daily_deduction} kcal")
        logger.info(f"  Selected Meals (from config): {config.selected_meals}")
        logger.info(f"{'='*60}")

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
        # We now pass ALL remaining meals to the LLM/Algorithm so it has full context
        # But we pass 'selected' list so it knows where to prioritize cuts
        selected = config.selected_meals or ["breakfast", "lunch", "dinner", "snacks"]
        selected = [s.lower() for s in selected]
        
        remaining_items = [
            m for m in base_plan 
            if m.meal_id.lower() not in completed_meal_ids
        ]
        
        # Calculate consumed
        consumed_cals = 0
        for m in base_plan:
            if m.meal_id.lower() in completed_meal_ids:
                nuts = m.nutrients or {}
                p = nuts.get('p', nuts.get('protein', 0))
                c = nuts.get('c', nuts.get('carbs', 0))
                f = nuts.get('f', nuts.get('fat', 0))
                cals = (p * 4) + (c * 4) + (f * 9)
                consumed_cals += cals
                
        remaining_budget = eff_calories - consumed_cals
        
        logger.info(f"FEAST OVERRIDES: Effective calories: {eff_calories}, Consumed: {consumed_cals}, Remaining budget: {remaining_budget}")
        logger.info(f"FEAST OVERRIDES: Completed meals: {completed_meal_ids}, Remaining meals: {[m.meal_id for m in remaining_items]}")
        logger.info(f"FEAST OVERRIDES: Selected for adjustment: {selected}")
        
        # 5. Generate Overrides
        # Strategy Change: Isolated Debt Logic
        # We pass the daily_deduction directly. The goal is to remove this amount from the selected meals.
        debt_target = config.daily_deduction
        
        overrides = []
        try:
            # Try LLM first
            try:
                overrides = self._generate_overrides_via_llm(config, remaining_items, debt_target, target_date, selected)
            except Exception as e:
                logger.error(f"LLM Override Gen failed: {e}. Fallback to ratio.")
                overrides = self._generate_overrides_via_ratio(config, remaining_items, debt_target, target_date, selected)
        except Exception as heavy_fail:
             logger.error(f"CRITICAL: Even fallback ratio failed: {heavy_fail}")
             overrides = [] # Proceed without overrides rather than crashing
            
        # 6. Save Overrides
        for ov in overrides:
            self.db.merge(ov) # Upsert
            
        self.db.flush()

    def _generate_overrides_via_llm(self, config: FeastConfig, remaining_items: list[MealPlan], budget: float, target_date: date, selected_ids: list):
        """
        Uses LLM to smartly adjust meals to fit budget.
        Returns list of FeastMealOverride objects.
        """
        if not remaining_items:
            return []

        # Prepare context for LLM
        current_planned = 0
        for m in remaining_items:
            nuts = m.nutrients or {}
            p = nuts.get('p', nuts.get('protein', 0))
            c = nuts.get('c', nuts.get('carbs', 0))
            f = nuts.get('f', nuts.get('fat', 0))
            current_planned += (p * 4) + (c * 4) + (f * 9)
        diff = budget - current_planned

        logger.info(f"\n{'='*60}")
        logger.info(f"FEAST MODE: LLM OVERRIDE GENERATION")
        logger.info(f"  Deduction Target: {budget} kcal")
        logger.info(f"  Current planned in remaining meals: {current_planned} kcal")
        logger.info(f"  Selected IDs: {selected_ids}")
        logger.info(f"{'='*60}")
        
        if abs(diff) < 20:  
            return [] # No adjustment needed (Wait, for debt logic, diff is just the debt?)
            
        # For Debt Logic: "budget" param is actually "deduction_target"
        target_deduction = budget 
        if target_deduction <= 0: return []

        phase = "FEAST_DAY" if target_date == config.event_date else "BANKING"
        selected_text = ", ".join(selected_ids or []) if selected_ids else "ALL"
        
        items_data = []
        for m in remaining_items:
            nuts = m.nutrients or {}
            p = float(nuts.get('p', nuts.get('protein', 0)))
            c = float(nuts.get('c', nuts.get('carbs', 0)))
            f = float(nuts.get('f', nuts.get('fat', 0)))
            
            # Auto-calc calories if missing
            base_cals = round(nuts.get('calories', 0))
            if base_cals == 0:
                base_cals = round((p * 4) + (c * 4) + (f * 9))

            is_selected = m.meal_id.lower() in selected_ids
            items_data.append({
                "meal_id": m.meal_id,
                "dish_name": m.dish_name,
                "is_selected_for_adjustment": is_selected,
                "base_calories": base_cals,
                "macros": {"p": p, "c": c, "f": f},
                "protein": p, "carbs": c, "fat": f, # redundancy for LLM clarity
                "portion_size": m.portion_size
            })
            
        logger.info(f"FEAST LLM: Sending {len(items_data)} items to LLM:")
        for item in items_data:
            logger.info(f"  {item['meal_id']}: {item['base_calories']} kcal, P={item['protein']:.1f} C={item['carbs']:.1f} F={item['fat']:.1f}, selected={item['is_selected_for_adjustment']}")
            
        from app.utils.llm_prompts.feast_prompts import FEAST_ADJUSTMENT_SYSTEM_PROMPT
        
        system_prompt = FEAST_ADJUSTMENT_SYSTEM_PROMPT
        user_prompt = f"""Event: {config.event_name} ({phase})
Context:
- Calorie Debt to Pay: {target_deduction:.0f} kcal
- User Selected Meals for Payment: {selected_text}

Meals Available:
{json.dumps(items_data, indent=2)}

RULES:
1. You are only allowed to edit these specific Meal IDs: {selected_text}.
2. Treat the 'Calorie Debt' ({target_deduction} kcal) as a debt to be divided among these selected meals.
3. If a meal falls below 75 calories after adjustment, set it to 0 and explain in the note: 'Skipped to meet calorie goals'.
4. STRICT: If a meal ID is not in the list, return it exactly as it is in the input. Do not change a single calorie.
5. Return ALL meals in the JSON, even if unchanged.

Adjust calories, protein, carbs, fat, portion_size.
"""
        # DEBUG: Log the full prompt to verify what LLM is receiving
        logger.info("=== FEAST MODE LLM PROMPT START ===")
        logger.info(user_prompt)
        logger.info("=== FEAST MODE LLM PROMPT END ===")

        response = llm_service.call_llm_json(
            system_prompt=system_prompt, 
            user_prompt=user_prompt,
            temperature=0.1
        )
        
        logger.info(f"FeastMode: LLM Raw Response: {response}")
        
        if not response or "adjusted_meals" not in response:
            raise ValueError("Invalid LLM response")
            
        results = []
        meal_map = {m.meal_id.lower(): m for m in remaining_items}
        
        for adj in response["adjusted_meals"]:
            mid = adj.get("meal_id", "").lower()
            if mid not in meal_map: continue
            
            # STRICT FILTER: Ignore any LLM hallucination that touches unselected meals
            if selected_ids and mid not in selected_ids:
                logger.warning(f"FeastMode: LLM returned update for unselected meal '{mid}'. Ignoring strict constraint.")
                continue

            
            # Map back to Override model
            adj_protein = float(adj.get("protein", 0) or adj.get("p", 0))
            adj_carbs = float(adj.get("carbs", 0) or adj.get("c", 0))
            adj_fat = float(adj.get("fat", 0) or adj.get("f", 0))
            adjusted_calories = float(adj.get("calories", 0) or adj.get("cal", 0))
            
            # Safety fallback: if LLM returned 0 calories but has macros, compute from macros
            if adjusted_calories == 0 and (adj_protein > 0 or adj_carbs > 0 or adj_fat > 0):
                adjusted_calories = round((adj_protein * 4) + (adj_carbs * 4) + (adj_fat * 9))
                logger.warning(f"FEAST LLM: Calories missing for '{mid}', computed from macros: {adjusted_calories} kcal")
            
            override = FeastMealOverride(
                feast_config_id=config.id,
                user_id=config.user_id,
                override_date=target_date,
                meal_id=mid,
                adjusted_calories=adjusted_calories,
                adjusted_protein=adj_protein,
                adjusted_carbs=adj_carbs,
                adjusted_fat=adj_fat,
                adjusted_portion_size=adj.get("portion_size", ""),
                adjustment_note=adj.get("note", ""),
                adjustment_method="llm"
            )
            results.append(override)

        logger.info(f"FEAST LLM: Generated {len(results)} overrides:")
        for ov in results:
            logger.info(f"  {ov.meal_id}: {ov.adjusted_calories:.0f} kcal (P={ov.adjusted_protein:.1f} C={ov.adjusted_carbs:.1f} F={ov.adjusted_fat:.1f}) - {ov.adjustment_note}")
        return results

    def _generate_overrides_via_ratio(self, config: FeastConfig, remaining_items: list[MealPlan], budget: float, target_date: date, selected_ids: list):
        """
        Fallback method using Isolated Debt Redistribution.
        'budget' here is actually the 'deduction_target' (Debt).
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"FEAST MODE: RATIO FALLBACK OVERRIDE GENERATION")
        logger.info(f"  Deduction Target: {budget} kcal")
        logger.info(f"  Selected Meals: {selected_ids}")
        logger.info(f"{'='*60}")
        deduction_target = budget
        
        # 0. Prep Data
        meal_cals = {}
        for m in remaining_items:
            nuts = m.nutrients or {}
            p = nuts.get('p', nuts.get('protein', 0))
            c = nuts.get('c', nuts.get('carbs', 0))
            f = nuts.get('f', nuts.get('fat', 0))
            cals = (p * 4) + (c * 4) + (f * 9)
            meal_cals[m.meal_id.lower()] = cals

        if deduction_target <= 0: return []

        # 1. Isolate Eligible Meals
        eligible_meals = [mid for mid in meal_cals.keys() if mid in selected_ids]
        
        logger.info(f"FEAST RATIO: Eligible meals: {eligible_meals}, Meal calories: {meal_cals}")
        
        if not eligible_meals:
            logger.warning("FEAST RATIO: No selected meals available to pay debt.")
            return [] # Cannot deduct anything

        # 2. Iterative Deduction Loop
        current_debt = deduction_target
        final_adjustments = {}
        
        # Initialize adjustments with original values (non-selected are locked)
        for mid, cals in meal_cals.items():
            final_adjustments[mid] = cals

        # List of eligible meals to track who is still "in the game"
        active_pool = eligible_meals[:]
        
        # Safety loop count
        for _ in range(10):
            if current_debt <= 1 or not active_pool:
                break
                
            share = current_debt / len(active_pool)
            
            # Check for droppers
            any_dropped = False
            next_pool = []
            
            for mid in active_pool:
                original_cals = meal_cals[mid]
                projected = original_cals - share
                
                # Threshold Rule: Human Logic check
                if projected < 75:
                    # Drop this meal
                    final_adjustments[mid] = 0
                    current_debt -= original_cals # Entire meal pays the debt
                    any_dropped = True
                    # Do NOT add to next_pool
                else:
                    next_pool.append(mid)
            
            if any_dropped:
                # Restart distribution with new debt and new pool
                active_pool = next_pool
                # Loop continues to recalculate share
            else:
                # Stable! Everyone can pay their share.
                for mid in active_pool:
                    original_cals = meal_cals[mid]
                    final_adjustments[mid] = original_cals - share
                current_debt = 0 # Paid off
                break
        
        # Final Guard: Check results
        # If active_pool is empty but debt remains, we stop (unselected are locked).
        
        logger.info(f"FEAST RATIO: Final adjustments: {final_adjustments}")
        
        results = []
        for m in remaining_items:
            mid = m.meal_id.lower()
            nuts = m.nutrients or {}
            orig_cal = meal_cals.get(mid, 0)
            
            new_cal = final_adjustments.get(mid, orig_cal)
            
            # Calculate Ratio for nutrient scaling
            if orig_cal > 0:
                ratio = new_cal / orig_cal
            else:
                ratio = 0
            
            note = f"Auto-scaled (Debt Logic)"
            if new_cal == 0 and orig_cal > 0:
                 note = "Skipped to meet calorie goals"
            
            # Scale nutrients
            p = nuts.get('p', nuts.get('protein', 0))
            c = nuts.get('c', nuts.get('carbs', 0))
            f = nuts.get('f', nuts.get('fat', 0))
            
            new_p = p * ratio
            new_c = c * ratio
            new_f = f * ratio
            
            # Scale portion string
            import re
            new_portion = m.portion_size
            if m.portion_size:
                new_portion = re.sub(r'\b(\d+(\.\d+)?)\b', 
                    lambda match: f"{float(match.group(1)) * ratio:.0f}", 
                    m.portion_size
                )
            if new_cal == 0: new_portion = "Skipped"

            override = FeastMealOverride(
                feast_config_id=config.id,
                user_id=config.user_id,
                override_date=target_date,
                meal_id=mid,
                adjusted_calories=new_cal,
                adjusted_protein=new_p,
                adjusted_carbs=new_c,
                adjusted_fat=new_f,
                adjusted_portion_size=new_portion,
                adjustment_note=note,
                adjustment_method="ratio_debt"
            )
            results.append(override)
        
        logger.info(f"FEAST RATIO: Generated {len(results)} overrides:")
        for ov in results:
            logger.info(f"  {ov.meal_id}: {ov.adjusted_calories:.0f} kcal (P={ov.adjusted_protein:.1f} C={ov.adjusted_carbs:.1f} F={ov.adjusted_fat:.1f}) - {ov.adjustment_note}")
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

    def inject_feast_workout_into_plan(self, user_id: int, workout_plan_schedule: dict, reference_date: date = None) -> dict:
        """
        Injects the Feast Mode workout into the provided weekly_schedule dictionary 
        if the event date falls on one of the schedule days AND within the same week as reference_date.
        """
        config = self.get_active_config(user_id)
        if not config or not config.feast_workout_data:
            return workout_plan_schedule

        if not reference_date:
            reference_date = date.today()
            
        # Check Week Alignment
        # Calculate start of week (Monday) for both dates
        event_week_start = config.event_date - timedelta(days=config.event_date.weekday())
        ref_week_start = reference_date - timedelta(days=reference_date.weekday())
        
        if event_week_start != ref_week_start:
            # Event is in a different week -> Do not inject
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
            "event_name": config.event_name,
            "original_diet_snapshot": config.original_diet_snapshot,
            "meal_breakdown": config.original_diet_snapshot.get("meals") if config.original_diet_snapshot else None
        }
