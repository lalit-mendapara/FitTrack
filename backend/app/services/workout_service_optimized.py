"""
Optimized Workout Service with:
- Async/Celery task support
- Exercise database caching
- Reduced LLM token usage (no full exercise list in prompt)
- Semantic matching for exercise resolution
"""

import json
import logging
import sys
from typing import Optional
from sqlalchemy.orm import Session
from datetime import date, datetime

from app.models.user_profile import UserProfile
from app.models.workout_plan import WorkoutPlan
from app.models.workout_plan_history import WorkoutPlanHistory
from app.models.workout_preferences import WorkoutPreferences
from app.models.tracking import WorkoutLog, WorkoutSession
from app.schemas.workout_plan import WorkoutPlanRequestData

from app.services import llm_service
from app.utils.nutrition_calc import calculate_bmr, calculate_target_workout_burn, calculate_active_exercise_burn
from app.utils.exercise_cache import (
    get_exercise_maps,
    find_exercise_by_name_fuzzy,
    get_exercises_by_experience_cached,
    get_cardio_exercises_cached
)

# Langfuse tracing
observe = lambda *args, **kwargs: (lambda f: f)
if sys.version_info < (3, 14):
    try:
        from langfuse import observe
    except ImportError:
        pass

logger = logging.getLogger(__name__)


@observe(name="generate_workout_plan_optimized", as_type="generation")
def generate_workout_plan_optimized(
    db: Session, 
    request_data: WorkoutPlanRequestData,
    task=None  # Celery task for progress updates
):
    """
    Optimized workout plan generation with caching and reduced token usage.
    
    Key optimizations:
    1. Uses cached exercise database (no repeated DB queries)
    2. Doesn't send full exercise list to LLM (saves tokens)
    3. Uses semantic matching to resolve LLM-generated exercise names
    4. Single DB commit for all changes
    5. Optional Celery task progress updates
    """
    user_id = request_data.user_id
    prefs = request_data.workout_preferences
    custom_prompt = request_data.custom_prompt
    
    logger.info(f"[OPTIMIZED] Generating workout plan for user {user_id}")
    
    if task:
        task.update_state(state='PROCESSING', meta={'status': 'Validating request...', 'progress': 15})
    
    # 1. Skip expensive custom prompt validation - let LLM handle it inline
    # (Optimization: removed separate validate_user_prompt LLM call)
    
    # 2. Get User Profile & Update Preferences
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        raise ValueError("UserProfile not found.")
    
    if task:
        task.update_state(state='PROCESSING', meta={'status': 'Loading user profile...', 'progress': 25})
    
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
    
    # 3. Calculate Targets
    age = getattr(profile.user, 'age', 25) if profile.user else 25
    gender = getattr(profile.user, 'gender', 'male') if profile.user else 'male'
    
    bmr = calculate_bmr(profile.weight, profile.height, age, gender)
    target_burn = calculate_target_workout_burn(bmr, profile.activity_level, prefs.days_per_week)
    
    if task:
        task.update_state(state='PROCESSING', meta={'status': 'Preparing workout context...', 'progress': 35})
    
    # 4. OPTIMIZATION: Use cached exercises, don't send full list to LLM
    # Instead, send only general guidelines and let LLM generate standard exercise names
    exercises_cached = get_exercises_by_experience_cached(prefs.experience_level)
    cardio_cached = get_cardio_exercises_cached()
    
    # Build minimal context (just categories, not full list)
    muscle_groups = set()
    equipment_types = set()
    for ex in exercises_cached:
        if ex.get('muscle_group'):
            muscle_groups.add(ex['muscle_group'])
        if ex.get('equipment'):
            equipment_types.add(ex['equipment'])
    
    equipment_context = f"Available equipment: {', '.join(sorted(equipment_types))}" if equipment_types else ""
    muscle_context = f"Target muscle groups: {', '.join(sorted(muscle_groups))}" if muscle_groups else ""
    
    # 5. Check for active Social Event (Feast Mode)
    from app.services.social_event_service import get_active_event
    
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
    
    # 6. Build Optimized Prompts (no exercise list)
    existing_plan_context = ""
    if custom_prompt:
        existing = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
        if existing and existing.weekly_schedule:
            existing_plan_context = f"\nCURRENT PLAN:\n{json.dumps(existing.weekly_schedule)[:500]}..."
    
    # Determine weekly day ordering
    all_day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    if request_data.start_from_today:
        today_weekday = datetime.today().weekday()
        rotated_days = all_day_names[today_weekday:] + all_day_names[:today_weekday]
    else:
        rotated_days = list(all_day_names)
    
    day_mapping_lines = ", ".join([f'"day{i+1}": "{d}"' for i, d in enumerate(rotated_days)])
    
    # Sunday rest constraint
    sunday_rest_rule = ""
    if prefs.days_per_week < 7:
        sunday_rest_rule = """
⛔ SUNDAY REST RULE:
- Sunday MUST be a REST/RECOVERY day. Do NOT schedule any workout on Sunday.
- Mark Sunday as: {"day_name": "Sunday", "workout_name": "Rest Day", "primary_muscle_group": "Recovery", "focus": "Rest", "exercises": [], "cardio_exercises": [], "session_duration_min": 0}
"""
    
    system_prompt = "You are a professional fitness coach. Return strictly valid JSON. Use standard exercise names from fitness science."
    
    user_prompt = f"""
# ROLE
You are a professional Fitness Coach creating a personalized workout plan.

# CONTEXT
- User Profile: Weight: {profile.weight}kg, Height: {profile.height}cm, Goal: {profile.fitness_goal}
- Preferences: {prefs.experience_level}, {prefs.days_per_week} days/week, {prefs.session_duration_min} mins/session
- Health Restrictions: "{prefs.health_restrictions}"
- {equipment_context}
- {muscle_context}
{existing_plan_context}

# TASK
Create a 7-day weekly schedule with exactly {prefs.days_per_week} workout days.
Custom instructions: "{custom_prompt if custom_prompt else 'None'}"

{social_context}

# WEEKLY DAY ORDER (CRITICAL)
{day_mapping_lines}
{sunday_rest_rule}

# HEALTH & SAFETY CONSTRAINTS
⛔ STRICT PROHIBITION:
1. IDENTIFY affected muscle groups/joints from health restrictions
2. EXCLUDE exercises targeting injured areas (direct or indirect)
3. OMIT muscle group days if severely restricted

Examples:
- Knee Injury: NO Squats, Lunges, Leg Press, Jumping
- Shoulder Injury: NO Overhead Press, Bench Press, Push-ups
- Lower Back Pain: NO Deadlifts, Bent-over Rows, Heavy Squats

# EXERCISE SELECTION
Use standard exercise names from fitness science (e.g., "Bench Press", "Squats", "Deadlift", "Running", "Cycling").
Do NOT invent exercises. Use well-known compound and isolation movements.

# FORMATTING RULES
1. Include at least 1 cardio exercise per workout day
2. Each exercise MUST have "instructions" with exactly 3 tips (Safety, Performance, Benefits)
3. Group exercises by muscle group (3-5 exercises per group)
4. Output exactly 7 days (day1 through day7)
5. Non-workout days: Rest/Recovery
6. Return ONLY valid JSON

=== OUTPUT JSON ===
{{
  "workout_plan": {{
    "plan_name": "8-Week {profile.fitness_goal} Program",
    "primary_goal": "{profile.fitness_goal}",
    "duration_weeks": 8,
    "weekly_schedule": {{
      "day1": {{
         "day_name": "{rotated_days[0]}",
         "workout_name": "Push Day",
         "primary_muscle_group": "Chest & Triceps",
         "focus": "Strength",
         "exercises": [
           {{
             "exercise": "Bench Press",
             "sets": 3,
             "reps": "10-12",
             "rest_sec": 60,
             "instructions": [
               "Safety: Keep back flat on bench",
               "Performance: Lower bar to chest with control",
               "Benefits: Builds chest, shoulders, triceps"
             ]
           }}
         ],
         "cardio_exercises": [
           {{
             "exercise": "Running",
             "duration": "10 mins",
             "intensity": "Moderate",
             "notes": "Warm-up",
             "instructions": [
               "Safety: Warm up properly",
               "Performance: Maintain steady pace",
               "Benefits: Cardiovascular health"
             ]
           }}
         ],
         "session_duration_min": {prefs.session_duration_min}
      }},
      "day2": {{ "day_name": "{rotated_days[1]}", "..." : "..." }},
      "day3": {{ "day_name": "{rotated_days[2]}", "..." : "..." }},
      "day4": {{ "day_name": "{rotated_days[3]}", "..." : "..." }},
      "day5": {{ "day_name": "{rotated_days[4]}", "..." : "..." }},
      "day6": {{ "day_name": "{rotated_days[5]}", "..." : "..." }},
      "day7": {{ "day_name": "{rotated_days[6]}", "..." : "..." }}
    }},
    "progression_guidelines": ["Increase weight by 2.5-5% weekly", "Add 1 rep when hitting upper range"],
    "cardio_recommendations": ["20 mins LISS on rest days", "HIIT once weekly"]
  }}
}}
"""
    
    if task:
        task.update_state(state='PROCESSING', meta={'status': 'Calling AI to generate plan...', 'progress': 50})
    
    # 7. Call LLM (optimized prompt, fewer tokens)
    response_data = llm_service.call_llm_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=20000
    )
    
    if not response_data or "workout_plan" not in response_data:
        raise ValueError("Failed to generate workout plan from LLM")
    
    generated_plan = response_data["workout_plan"]
    
    if task:
        task.update_state(state='PROCESSING', meta={'status': 'Mapping exercises to database...', 'progress': 70})
    
    # 8. Post-Processing: Use CACHED exercise maps for fuzzy matching
    ex_map, norm_ex_map = get_exercise_maps()
    
    # Process each day's exercises
    for day_key, day_data in generated_plan.get("weekly_schedule", {}).items():
        if not isinstance(day_data, dict):
            continue
        
        # Process regular exercises
        for ex in day_data.get("exercises", []):
            ex_name = ex.get("exercise", "")
            matched_ex = find_exercise_by_name_fuzzy(ex_name, ex_map, norm_ex_map)
            
            if matched_ex:
                ex["image_url"] = matched_ex.get("image_url", "")
                ex["exercise_id"] = matched_ex.get("id")
                # Calculate calorie burn
                sets = ex.get("sets", 3)
                reps_str = str(ex.get("reps", "10"))
                avg_reps = int(reps_str.split("-")[0]) if "-" in reps_str else int(reps_str) if reps_str.isdigit() else 10
                duration_min = (sets * avg_reps * 3) / 60  # Rough estimate
                ex["calories_burned"] = round(calculate_active_exercise_burn(
                    profile.weight, duration_min, matched_ex.get("calories_per_min", 5.0)
                ))
            else:
                # Exercise not in DB - use defaults
                ex["image_url"] = ""
                ex["exercise_id"] = None
                ex["calories_burned"] = 50  # Default estimate
        
        # Process cardio exercises
        for cardio in day_data.get("cardio_exercises", []):
            cardio_name = cardio.get("exercise", "")
            matched_cardio = find_exercise_by_name_fuzzy(cardio_name, ex_map, norm_ex_map)
            
            if matched_cardio:
                cardio["image_url"] = matched_cardio.get("image_url", "")
                cardio["exercise_id"] = matched_cardio.get("id")
                # Parse duration
                duration_str = cardio.get("duration", "10 mins")
                duration_min = int(''.join(filter(str.isdigit, duration_str))) if duration_str else 10
                cardio["calories_burned"] = round(calculate_active_exercise_burn(
                    profile.weight, duration_min, matched_cardio.get("calories_per_min", 8.0)
                ))
            else:
                cardio["image_url"] = ""
                cardio["exercise_id"] = None
                duration_str = cardio.get("duration", "10 mins")
                duration_min = int(''.join(filter(str.isdigit, duration_str))) if duration_str else 10
                cardio["calories_burned"] = round(duration_min * 8)  # Default 8 kcal/min
    
    if task:
        task.update_state(state='PROCESSING', meta={'status': 'Merging with workout history...', 'progress': 85})
    
    # 9. History Merging (preserve past completed workouts)
    existing_plan_db = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
    
    if existing_plan_db and existing_plan_db.weekly_schedule and not request_data.ignore_history:
        try:
            old_schedule = existing_plan_db.weekly_schedule
            new_schedule = generated_plan.get("weekly_schedule", {})
            
            today_date = datetime.today().date()
            today_idx = datetime.today().weekday()
            
            # Check for logged workouts
            logged_workout_dates = {
                row[0] for row in db.query(WorkoutLog.date)
                .filter(WorkoutLog.user_id == user_id, WorkoutLog.date < today_date)
                .distinct().all() if row[0] is not None
            }
            logged_session_dates = {
                row[0] for row in db.query(WorkoutSession.date)
                .filter(WorkoutSession.user_id == user_id, WorkoutSession.date < today_date)
                .distinct().all() if row[0] is not None
            }
            
            has_history = bool(logged_workout_dates or logged_session_dates)
            
            if has_history:
                # Preserve past days (before today)
                for i in range(today_idx):
                    day_key = f"day{i+1}"
                    if day_key in old_schedule:
                        new_schedule[day_key] = old_schedule[day_key]
                
                logger.info(f"[HISTORY] Preserved {today_idx} past workout days")
        except Exception as e:
            logger.error(f"[HISTORY] Merge failed: {e}")
    
    if task:
        task.update_state(state='PROCESSING', meta={'status': 'Saving workout plan...', 'progress': 95})
    
    # 10. Save to Database (single commit optimization)
    if existing_plan_db:
        # Update existing
        existing_plan_db.plan_name = generated_plan.get("plan_name", "Workout Plan")
        existing_plan_db.primary_goal = generated_plan.get("primary_goal", profile.fitness_goal)
        existing_plan_db.duration_weeks = generated_plan.get("duration_weeks", 8)
        existing_plan_db.weekly_schedule = generated_plan.get("weekly_schedule", {})
        existing_plan_db.progression_guidelines = generated_plan.get("progression_guidelines", [])
        existing_plan_db.cardio_recommendations = generated_plan.get("cardio_recommendations", [])
        plan_to_return = existing_plan_db
    else:
        # Create new
        new_plan = WorkoutPlan(
            user_profile_id=profile.id,
            plan_name=generated_plan.get("plan_name", "Workout Plan"),
            primary_goal=generated_plan.get("primary_goal", profile.fitness_goal),
            duration_weeks=generated_plan.get("duration_weeks", 8),
            weekly_schedule=generated_plan.get("weekly_schedule", {}),
            progression_guidelines=generated_plan.get("progression_guidelines", []),
            cardio_recommendations=generated_plan.get("cardio_recommendations", [])
        )
        db.add(new_plan)
        plan_to_return = new_plan
    
    # Save history snapshot
    history_entry = WorkoutPlanHistory(
        user_profile_id=profile.id,
        plan_name=generated_plan.get("plan_name", "Workout Plan"),
        primary_goal=generated_plan.get("primary_goal", profile.fitness_goal),
        duration_weeks=generated_plan.get("duration_weeks", 8),
        weekly_schedule=generated_plan.get("weekly_schedule", {}),
        progression_guidelines=generated_plan.get("progression_guidelines", []),
        cardio_recommendations=generated_plan.get("cardio_recommendations", [])
    )
    db.add(history_entry)
    
    # Single commit for all changes
    db.commit()
    db.refresh(plan_to_return)
    
    logger.info(f"[OPTIMIZED] Workout plan generated successfully for user {user_id}")
    
    return plan_to_return
