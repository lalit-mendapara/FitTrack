
import json
import logging
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import date

from app.models.user_profile import UserProfile
from app.models.workout_plan import WorkoutPlan
from app.models.workout_plan_history import WorkoutPlanHistory
from app.models.workout_preferences import WorkoutPreferences
from app.models.exercise import Exercise
from app.schemas.workout_plan import WorkoutPlanRequestData, ProfileData

from app.services import llm_service
from app.utils.nutrition_calc import calculate_bmr, calculate_target_workout_burn, calculate_active_exercise_burn

logger = logging.getLogger(__name__)

"""
Workout Service
---------------
Orchestrates the generation of Workout Plans.
1. Validates user request.
2. Updates workout preferences.
3. Fetches relevant exercises.
4. Calls LLM to compose the weekly schedule.
5. Post-processes (Calorie burn calc, Image mapping).
6. Saves to DB.
"""

def _normalize_name(name: str) -> str:
    """Normalize exercise name: lowercase, remove non-alphanumeric."""
    if not name:
        return ""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def get_exercises_by_experience(db: Session, experience_level: str) -> List[Exercise]:
    """Filter exercises by difficulty based on user experience."""
    exp_lower = (experience_level or "beginner").lower().strip()
    
    allowed = ["Beginner"]
    if exp_lower == "intermediate":
        allowed.extend(["Intermediate"])
    elif exp_lower == "advanced":
        allowed.extend(["Intermediate", "Advanced"])
        
    return db.query(Exercise).filter(Exercise.difficulty.in_(allowed)).limit(100).all()

def generate_workout_plan(db: Session, request_data: WorkoutPlanRequestData):
    """
    Main orchestrator for workout plan generation.
    """
    user_id = request_data.user_id
    prefs = request_data.workout_preferences
    custom_prompt = request_data.custom_prompt
    
    logger.info(f"Generating workout plan for user {user_id}")
    
    # 1. Validate Prompt
    if custom_prompt:
        llm_service.validate_user_prompt(custom_prompt, context_type="workout")
        
    # 2. Get User Profile & Update Preferences
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        raise ValueError("UserProfile not found.")
        
    # Update/Create Preferences record
    db_prefs = db.query(WorkoutPreferences).filter(WorkoutPreferences.user_profile_id == profile.id).first()
    if not db_prefs:
        db_prefs = WorkoutPreferences(user_profile_id=profile.id)
        db.add(db_prefs)
    
    # Sync fields
    db_prefs.experience_level = prefs.experience_level
    db_prefs.days_per_week = prefs.days_per_week
    db_prefs.session_duration_min = prefs.session_duration_min
    db_prefs.health_restrictions = prefs.health_restrictions
    db.commit()
    db.refresh(db_prefs)
    
    # 3. Calculate Targets (Burn)
    # Using existing utility
    age = getattr(profile.user, 'age', 25) if profile.user else 25
    gender = getattr(profile.user, 'gender', 'male') if profile.user else 'male'
    
    bmr = calculate_bmr(profile.weight, profile.height, age, gender)
    target_burn = calculate_target_workout_burn(bmr, profile.activity_level, prefs.days_per_week)
    
    # 4. Fetch Exercises
    exercises = get_exercises_by_experience(db, prefs.experience_level)
    cardio_exercises = db.query(Exercise).filter(Exercise.category == "Cardio").all()
    
    # Build Context
    ex_context = "\n".join([f"- {e.name} ({e.category}) - Target: {e.primary_muscle}" for e in exercises])
    cardio_context = "\n".join([f"- {c.name} (Cardio)" for c in cardio_exercises])
    
    # 5. Build Prompts
    existing_plan_context = ""
    # If custom prompt, try to get existing plan to modify
    if custom_prompt:
        existing = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
        if existing and existing.weekly_schedule:
             # Minimal context
             existing_plan_context = f"\nCURRENT PLAN:\n{json.dumps(existing.weekly_schedule)[:500]}..."

    # Check for active Social Event to inject context
    from app.services.social_event_service import get_active_event
    from datetime import date
    
    # We need to know if the PLAN covers the event date.
    # For now, let's assume the event is within the next 7 days (the plan duration).
    active_event = get_active_event(db, user_id, date.today())
    social_context = ""
    
    if active_event:
        social_context = f"""
        🚨 SPECIAL EVENT DETECTED: "{active_event.event_name}" on {active_event.event_date}.
        GOAL: The user is "banking" calories for this big meal.
        INSTRUCTION: On {active_event.event_date.strftime('%A')}, you MUST schedule a "GLYCOGEN DEPLETION" workout (e.g., High Volume Leg Day or Full Body Depletion).
        - Focus: Compound movements, higher reps (12-15), metabolic stress.
        - Objective: Deplete muscle glycogen so the upcoming feast goes to muscle repair, not fat storage.
        """

    system_prompt = "You are a professional fitness coach. Return strictly valid JSON."
    
    user_prompt = f"""
    # ROLE (Persona)
    You are a professional Fitness Coach.

    # CONTEXT
    - User Profile: Weight: {profile.weight}kg, Goal: {profile.fitness_goal}
    - Preferences: {prefs.experience_level}, {prefs.days_per_week} days/week, {prefs.session_duration_min} mins/session
    - Existing Plan Context: {existing_plan_context}
    
    # TASK (Goal)
    Create a detailed {prefs.days_per_week}-day workout split that:
    1. Aligns with the user's goal ({profile.fitness_goal}) and experience level.
    2. Includes specific warm-up and regular cardio.
    3. Adapts to user feedback: "{custom_prompt if custom_prompt else 'None'}"
    
    {social_context}

    # CONSTRAINTS (Health & Safety) - CRITICAL
    - Health Restrictions: "{prefs.health_restrictions}"
    
    ⛔ STRICT PROHIBITION PROTOCOL:
    1. IDENTIFY: specific muscle groups and joints affected by the health restrictions.
    2. EXCLUDE: 
       - DIRECTLY: Do NOT include ANY exercise that targets the injured area.
       - INDIRECTLY: Do NOT include ANY compound movement where the injured area is a secondary mover (e.g., No "Bench Press" for shoulder injuries).
    3. OMIT MUSCLE GROUP: If a muscle group is severely restricted (e.g. "Shoulder Injury"), DO NOT schedule a workout day focused on that muscle group.
       - Instead, focus on other unaffected areas (e.g. Legs, Core, Cardio).
    
    ⚠️ IF A SAFETY CONFLICT EXISTS OR YOU ARE UNSURE, OMIT THE EXERCISE. BETTER TO SKIP THAN INJURE.
    
    Examples of STRICT Exclusions:
    - Knee Injury: NO Squats, Lunges, Leg Press, Jumping, or High Impact Cardio.
    - Shoulder Injury: NO Overhead Press, Bench Press, Push-ups, Dips, or Upright Rows.
    - Lower Back Pain: NO Deadlifts, Bent-over Rows, Good Mornings, or Heavy Squats.
    
    If health restrictions are present, review EVERY exercise against them.

    # AVAILABLE EQUIPMENT & EXERCISES
    {ex_context}
    
    # AVAILABLE CARDIO
    {cardio_context}
    
    # FORMATTING RULES
    1. MANDATORY: Include at least 1 cardio exercise in 'cardio_exercises' per day.
    2. STRICT SELECTION: For 'cardio_exercises', pick explicitly from 'AVAILABLE CARDIO'.
    3. INSTRUCTIONS: Each exercise MUST have "instructions" with exactly 3 tips (Safety, Performance, Benefits).
    4. SEQUENCING: Group exercises by muscle group (4 exercises per group).
       - Example: Chest & Triceps -> 4 Chest exercises, then 4 Triceps exercises.
    5. OUTPUT: Strictly return valid JSON.

    === OUTPUT JSON ===
    {{
      "workout_plan": {{
        "plan_name": "...",
        "primary_goal": "{profile.fitness_goal}",
        "duration_weeks": 8,
        "weekly_schedule": {{
          "day1": {{
             "day_name": "Monday",
             "workout_name": "Push Day",
             "primary_muscle_group": "Chest & Triceps",
             "focus": "Strength",
             "exercises": [ {{"exercise": "Bench Press", "sets": 3, "reps": "10-12", "rest_sec": 60, "instructions": ["Safety: Keep your back flat on the bench", "Performance: Lower bar to chest with control", "Benefits: Builds chest, shoulders, and triceps strength"]}} ],
             "cardio_exercises": [ {{"exercise": "Running", "duration": "10 mins", "intensity": "Moderate", "notes": "Warm-up", "instructions": ["Safety: Warm up properly", "Performance: Maintain steady pace", "Benefits: Improves cardiovascular health"]}} ], 
             "session_duration_min": 60
          }}
        }},
        "progression_guidelines": ["Tip 1", "Tip 2"],
        "cardio_recommendations": ["Do 20 mins LISS on rest days", "HIIT once a week"]
      }}
    }}
    """
    
    # 6. Call LLM
    response_data = llm_service.call_llm_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2
    )

    if not response_data or "workout_plan" not in response_data:
        raise ValueError("Failed to generate workout plan.")
        
    generated_plan = response_data["workout_plan"]
    
    # 7. Post-Processing (Image Mapping & Calorie Calc)
    # Load all exercises for mapping (Efficiency note: optimize in future)
    all_exercises = db.query(Exercise).all()
    # Name -> object map
    ex_map = {ex.name.lower().strip(): ex for ex in all_exercises}
    # Normalized map for fuzzy matching
    norm_ex_map = {_normalize_name(ex.name): ex for ex in all_exercises}
    
    # --- HISTORY MERGING LOGIC START ---
    from datetime import datetime
    
    # 1. Fetch Existing Plan
    existing_plan_db = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
    
    print("\n" + "="*60)
    print(" WORKOUT PLAN MERGE - PRESERVING HISTORY")
    print("="*60)
    
    if existing_plan_db and existing_plan_db.weekly_schedule and not request_data.ignore_history:
        try:
            old_schedule = existing_plan_db.weekly_schedule
            new_schedule = generated_plan.get("weekly_schedule", {})
            
            # 0=Mon, 1=Tue, ..., 6=Sun
            today_idx = datetime.today().weekday() 
            print(f" [INFO] Today is index {today_idx} ({datetime.today().strftime('%A')})")
            
            # Map day keys (day1, day2...) to indices 0..6
            # We assume day1=Monday, day2=Tuesday based on standard logic, 
            # BUT we should check the 'day_name' inside if available, or just index.
            # Standard assumption: keys are ordered 1..7.
            
            # Helper to get index from key "day1" -> 0
            def get_day_idx(k):
                try:
                    return int(re.sub(r'\D', '', k)) - 1
                except:
                    return -1

            days_merged = 0
            
            # Check consistency (e.g. if days_per_week changed, don't merge)
            if len(old_schedule) != len(new_schedule):
                 print(" [WARN] Plan duration changed (Days mismatch). Skipping merge to avoid corruption.")
            else:
                for day_key in new_schedule.keys():
                    d_idx = get_day_idx(day_key)
                    
                    if 0 <= d_idx < today_idx:
                        # PAST DAY -> RESTORE OLD DATA
                        if day_key in old_schedule:
                            print(f" [MERGE] Restoring history for {day_key} (Past Day).")
                            new_schedule[day_key] = old_schedule[day_key]
                            days_merged += 1
                        else:
                            print(f" [WARN] Old plan missing {day_key}, keeping new.")
                    elif d_idx == today_idx:
                        print(f" [NEW]   Generating fresh plan for {day_key} (TODAY).")
                    else:
                        print(f" [NEW]   Generating fresh plan for {day_key} (Future).")
                
                # Apply merged schedule back to generated_plan
                generated_plan["weekly_schedule"] = new_schedule
                print(f" [DONE] Successfully restored {days_merged} past days.")
                
        except Exception as e:
            print(f" [ERROR] Merge failed: {e}. Proceeding with full new plan.")
    else:
        print(" [INFO] No existing plan found. Generating full fresh plan.")
        
    print("="*60 + "\n")
    # --- HISTORY MERGING LOGIC END ---

    schedule = generated_plan.get("weekly_schedule", {})
    
    for day_key, day_data in schedule.items():
        # Process Strength
        if "exercises" in day_data:
            for item in day_data["exercises"]:
                name = item.get("exercise", "").lower().strip()
                # Find exercise object
                # Find exercise object
                ex_obj = ex_map.get(name) 
                
                # Smart Fuzzy Match (Normalization)
                if not ex_obj:
                    norm_name = _normalize_name(name)
                    # 1. Try exact normalized match
                    ex_obj = norm_ex_map.get(norm_name)
                    
                    # 2. Try bidirectional substring match on normalized names
                    if not ex_obj:
                        ex_obj = next((ex for n_name, ex in norm_ex_map.items() if norm_name in n_name or n_name in norm_name), None)
                
                # Default values if unknown
                cat = ex_obj.category if ex_obj else "Strength"
                diff = ex_obj.difficulty if ex_obj else "Intermediate"
                muscle = ex_obj.primary_muscle if ex_obj else "General"
                image_url = ex_obj.image_url if ex_obj else None
                
                # Calculate Calories
                sets = int(item.get("sets", 3))
                reps = item.get("reps", "10")
                
                burn = calculate_active_exercise_burn(
                    user_weight_kg=profile.weight,
                    category=f"{cat} {muscle}",
                    difficulty=diff,
                    is_cardio=False,
                    sets=sets,
                    reps=reps,
                    exercise_name=name
                )
                
                item["calories_burned"] = burn
                item["image_url"] = image_url  # No fallback to avoid "old photo" confusion
                item["target_muscle"] = muscle
                
                # Ensure all required fields have values (defaults for missing)
                if "rest_sec" not in item or item["rest_sec"] is None:
                    item["rest_sec"] = 60
                if "sets" not in item or item["sets"] is None:
                    item["sets"] = 3
                if "reps" not in item or item["reps"] is None:
                    item["reps"] = "10-12"
                if "instructions" not in item or not item["instructions"]:
                    item["instructions"] = []

        # Process Cardio
        if "cardio_exercises" in day_data:
            for item in day_data["cardio_exercises"]:
                name = item.get("exercise", "").lower().strip()
                duration = item.get("duration", "20 mins")
                
                ex_obj = ex_map.get(name)
                
                # Smart Fuzzy Match for Cardio
                if not ex_obj:
                    norm_name = _normalize_name(name)
                    ex_obj = norm_ex_map.get(norm_name)
                    if not ex_obj:
                         ex_obj = next((ex for n_name, ex in norm_ex_map.items() if norm_name in n_name or n_name in norm_name), None)
                
                cat = ex_obj.category if ex_obj else "Cardio"
                diff = ex_obj.difficulty if ex_obj else "Intermediate"
                image_url = ex_obj.image_url if ex_obj else None
                
                burn = calculate_active_exercise_burn(
                    user_weight_kg=profile.weight,
                    category=f"{cat} {name}",
                    difficulty=diff,
                    is_cardio=True,
                    duration_str=duration,
                    exercise_name=name
                )
                
                item["calories_burned"] = burn
                item["image_url"] = image_url # No fallback
                
                # Ensure all required fields have values (defaults for missing)
                if "duration" not in item or not item["duration"]:
                    item["duration"] = "10 mins"
                if "intensity" not in item or not item["intensity"]:
                    item["intensity"] = "Moderate"
                if "notes" not in item or not item["notes"]:
                    item["notes"] = "-"
                if "instructions" not in item or not item["instructions"]:
                    item["instructions"] = []

    # 8. Save to DB
    db_plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
    if not db_plan:
        db_plan = WorkoutPlan(user_profile_id=profile.id)
        db.add(db_plan)
        
    db_plan.plan_name = generated_plan.get("plan_name", "Custom Plan")
    db_plan.duration_weeks = generated_plan.get("duration_weeks", 8)
    db_plan.primary_goal = generated_plan.get("primary_goal", profile.fitness_goal)
    db_plan.weekly_schedule = schedule
    db_plan.progression_guidelines = generated_plan.get("progression_guidelines", [])
    db_plan.cardio_recommendations = generated_plan.get("cardio_recommendations", [])
    
    db.commit()
    db.refresh(db_plan)

    # 8b. Save Snapshot to History (Persistent Storage)
    try:
        history_entry = WorkoutPlanHistory(
            user_profile_id=profile.id,
            workout_plan_snapshot=generated_plan
        )
        db.add(history_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save workout plan history: {e}")
        # Non-blocking error
    
    # 9. Return Response
    profile_data = ProfileData(
        weight_kg=profile.weight,
        height_cm=profile.height,
        target_weight_kg=profile.weight_goal or profile.weight,
        fitness_goal=profile.fitness_goal,
        activity_level=profile.activity_level
    )
    
    return {
        "workout_plan": generated_plan,
        "profile_data": profile_data.dict()
    }
def patch_limit_day_workout(db: Session, user_id: int, event_date: date):
    """
    Patches the user's current workout plan to inject a "Glycogen Depletion" workout 
    on the specific event date.
    """
    from datetime import date, timedelta
    
    # 1. Get Profile & Plan
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile: return
    
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
    if not plan or not plan.weekly_schedule: return
    
    # 2. Determine Day Key (e.g. "day6")
    # We assume the plan started... when? 
    # Current limitation: The plan is a "Weekly Schedule" (Day 1 - Day 7). 
    # It loops. We just need to know which Day of Week the event is.
    # Event Date -> Weekday (0=Mon, 6=Sun)
    # We map this to the plan's keys.
    
    weekday_map = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
    event_weekday_name = weekday_map[event_date.weekday()]
    
    target_key = None
    for key, day_data in plan.weekly_schedule.items():
        # Check if day_name matches
        if day_data.get("day_name") == event_weekday_name:
            target_key = key
            break
            
    if not target_key:
        return # Could not match day
        
    # 3. Create the Depletion Workout
    depletion_workout = {
        "day_name": event_weekday_name,
        "workout_name": "🔥 FEAST MODE: Glycogen Depletion",
        "primary_muscle_group": "Legs & Full Body",
        "focus": "Metabolic Depletion",
        "session_duration_min": 60,
        "exercises": [
            {
                "exercise": "Bodyweight Squats (High Reps)",
                "sets": 4,
                "reps": "20-25",
                "rest_sec": 45,
                "instructions": ["Constant tension", "No lockout at top", "Burn out the legs"],
                "target_muscle": "Quadriceps",
                "calories_burned": 150 # Est
            },
            {
                "exercise": "Walking Lunges",
                "sets": 3,
                "reps": "15 per leg",
                "rest_sec": 60,
                "instructions": ["Deep stretch", "Keep torso upright", "Focus on glutes/hams"],
                "target_muscle": "Glutes & Hamstrings",
                "calories_burned": 120
            },
            {
                "exercise": "Push-ups (AMRAP)",
                "sets": 3,
                "reps": "Failure",
                "rest_sec": 60,
                "instructions": ["Chest to floor", "Explosive up", "Max reps"],
                "target_muscle": "Chest",
                "calories_burned": 100
            },
            {
                "exercise": "Burpees",
                "sets": 3,
                "reps": "15",
                "rest_sec": 60,
                "instructions": ["Full body movement", "Jump high", "Get heart rate up"],
                "target_muscle": "Full Body",
                "calories_burned": 150
            }
        ],
        "cardio_exercises": [
            {
                "exercise": "HIIT Sprints",
                "duration": "15 mins",
                "intensity": "High",
                "notes": "30s Sprint / 30s Walk",
                "calories_burned": 200,
                "instructions": ["Max effort sprints", "Recover fully between"]
            }
        ]
    }
    
    # 4. Patch & Save
    # We must clone the dict to ensure SQLAlchemy detects change
    new_schedule = dict(plan.weekly_schedule)
    new_schedule[target_key] = depletion_workout
    
    plan.weekly_schedule = new_schedule
    # Also update history? Maybe not strict requirement for now.
    
    db.commit()
    logger.info(f"Patched workout for user {user_id} on {event_weekday_name} (Feast Mode)")


def restore_workout_plan(db: Session, user_id: int, event_date: date):
    """
    Restores the original workout for a specific date (undoing Feast Mode patch).
    Attempts to retrieve the original day from WorkoutPlanHistory.
    """
    from datetime import date
    
    # 1. Get Profile & Plan
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile: return
    
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
    if not plan or not plan.weekly_schedule: return
    
    # 2. Determine Day Key (e.g. "day6")
    weekday_map = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
    event_weekday_name = weekday_map[event_date.weekday()]
    
    target_key = None
    for key, day_data in plan.weekly_schedule.items():
        if day_data.get("day_name") == event_weekday_name:
            target_key = key
            break
            
    if not target_key:
        return 
        
    # 3. Fetch History Snapshot
    # Get latest history entry that ISN'T the current plan? No, history is static snapshot.
    history = db.query(WorkoutPlanHistory).filter(
        WorkoutPlanHistory.user_profile_id == profile.id
    ).order_by(WorkoutPlanHistory.created_at.desc()).first()
    
    if not history or not history.workout_plan_snapshot:
        logger.warning(f"No workout history found for user {user_id}. Cannot restore original workout.")
        return

    snapshot_schedule = history.workout_plan_snapshot.get("weekly_schedule", {})
    
    # 4. Restore
    if target_key in snapshot_schedule:
        original_day = snapshot_schedule[target_key]
        
        # Verify it matches the day name to be safe
        if original_day.get("day_name") == event_weekday_name:
            # Clone dict to trigger SQLAlchemy update
            new_schedule = dict(plan.weekly_schedule)
            new_schedule[target_key] = original_day
            plan.weekly_schedule = new_schedule
            
            db.commit()
            logger.info(f"Restored original workout for user {user_id} on {event_weekday_name} (Revert Feast Mode)")
        else:
            logger.warning(f"History mismatch: Key {target_key} is {original_day.get('day_name')} but needed {event_weekday_name}")
    else:
        logger.warning(f"Key {target_key} not found in workout history snapshot.")
