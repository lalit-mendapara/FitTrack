from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date as DateType, datetime
from app.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.tracking import FoodLog, WorkoutLog, WorkoutSession

router = APIRouter()

# --- Pydantic Schemas ---
class LogMealRequest(BaseModel):
    meal_name: str
    meal_type: Optional[str] = None
    calories: float
    protein: float
    carbs: float
    fat: float
    date: Optional[DateType] = None  # Changed from default=DateType.today()
    created_at: Optional[datetime] = None

class LogWorkoutRequest(BaseModel):
    exercise_name: str
    img_url: Optional[str] = None
    sets: Optional[str] = None
    reps: Optional[str] = None
    weight: Optional[float] = None
    muscle_group: Optional[str] = None
    notes: Optional[str] = None
    
    date: Optional[DateType] = None  # Changed from default=DateType.today()
    created_at: Optional[datetime] = None
    duration_min: Optional[int] = None
    calories_burned: Optional[float] = None

class LogWorkoutSessionRequest(BaseModel):
    date: Optional[DateType] = None  # Changed from default=DateType.today()
    duration_minutes: int
    created_at: Optional[datetime] = None

# --- Helper to get Local Time ---
def get_user_local_time(user: User):
    """
    Returns the current datetime in the user's timezone (naive).
    Defaults to UTC if timezone is invalid or not set.
    """
    import pytz
    
    profile = user.profile
    if isinstance(profile, list):
        profile = profile[0] if profile else None
        
    tz_name = getattr(profile, 'timezone', 'UTC')
    if not tz_name:
        tz_name = 'UTC'
        
    try:
        user_tz = pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        user_tz = pytz.UTC
        
    # Get current UTC time and convert to user's timezone
    server_now = datetime.now(pytz.UTC)
    user_now = server_now.astimezone(user_tz)
    
    # Return as naive datetime (strip tzinfo) because DB usually expects naive
    # or if we want to store it as "User's Wall Clock Time"
    return user_now.replace(tzinfo=None)


# --- Endpoints ---

@router.post("/log-meal", status_code=status.HTTP_201_CREATED)
def log_meal(
    request: LogMealRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log a meal to the user's history.
    """
    # Determine defaults based on user's timezone
    if not request.date or not request.created_at:
        local_now = get_user_local_time(current_user)
        
        final_date = request.date if request.date else local_now.date()
        final_created_at = request.created_at if request.created_at else local_now
    else:
        final_date = request.date
        final_created_at = request.created_at

    new_log = FoodLog(
        user_id=current_user.id,
        date=final_date,
        food_name=request.meal_name,
        meal_type=request.meal_type,
        calories=request.calories,
        protein=request.protein,
        carbs=request.carbs,
        fat=request.fat,
        created_at=final_created_at
    )
    
    db.add(new_log)
    db.commit()
    return {"message": "Meal logged successfully", "log_id": new_log.id}

@router.post("/log-workout", status_code=status.HTTP_201_CREATED)
def log_workout(
    request: LogWorkoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log a workout to the user's history.
    """
    # Determine defaults based on user's timezone
    if not request.date or not request.created_at:
        local_now = get_user_local_time(current_user)
        
        final_date = request.date if request.date else local_now.date()
        final_created_at = request.created_at if request.created_at else local_now
    else:
        final_date = request.date
        final_created_at = request.created_at

    new_log = WorkoutLog(
        user_id=current_user.id,
        date=final_date,
        exercise_name=request.exercise_name,
        img_url=request.img_url,
        sets=request.sets,
        reps=request.reps,
        weight=request.weight,
        muscle_group=request.muscle_group,
        notes=request.notes,
        duration_min=request.duration_min,
        calories_burned=request.calories_burned,
        created_at=final_created_at
    )

    db.add(new_log)
    db.commit()
    return {"message": "Workout logged successfully", "log_id": new_log.id}

@router.post("/log-workout-session", status_code=status.HTTP_201_CREATED)
def log_workout_session(
    request: LogWorkoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log or Update a workout session duration for a specific date.
    If a session already exists for this date, update it.
    """
    # Determine defaults based on user's timezone
    if not request.date:
        local_now = get_user_local_time(current_user)
        final_date = local_now.date()
    else:
        final_date = request.date

    # Check if session exists for this date
    existing_session = db.query(WorkoutSession).filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.date == final_date
    ).first()
    
    if existing_session:
        existing_session.duration_minutes = request.duration_minutes
        db.commit()
        return {"message": "Workout session updated", "session_id": existing_session.id}
    else:
        # For new session, if created_at not provided, use local time
        if not request.created_at:
            local_now = get_user_local_time(current_user)
            final_created_at = local_now
        else:
            final_created_at = request.created_at

        new_session = WorkoutSession(
            user_id=current_user.id,
            date=final_date,
            duration_minutes=request.duration_minutes,
            created_at=final_created_at
        )
            
        db.add(new_session)
        db.commit()
        return {"message": "Workout session logged", "session_id": new_session.id}

@router.delete("/log-meal/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a meal log.
    """
    log = db.query(FoodLog).filter(FoodLog.id == log_id, FoodLog.user_id == current_user.id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    db.delete(log)
    db.commit()
    return None

@router.delete("/daily-diet", status_code=status.HTTP_204_NO_CONTENT)
def delete_daily_diet_logs(
    date: DateType = Query(default=DateType.today()),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete all meal logs for the specified date.
    """
    db.query(FoodLog).filter(
        FoodLog.user_id == current_user.id,
        FoodLog.date == date
    ).delete()
    
    db.commit()
    return None

@router.delete("/log-workout/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a workout log.
    """
    log = db.query(WorkoutLog).filter(WorkoutLog.id == log_id, WorkoutLog.user_id == current_user.id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    db.delete(log)
    db.commit()
    return None

@router.delete("/daily-workout", status_code=status.HTTP_204_NO_CONTENT)
def delete_daily_workout_logs(
    date: DateType = Query(default=DateType.today()),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete all workout logs for the specified date.
    """
    db.query(WorkoutLog).filter(
        WorkoutLog.user_id == current_user.id,
        WorkoutLog.date == date
    ).delete()

    # Also delete session if exists
    from app.models.tracking import WorkoutSession
    db.query(WorkoutSession).filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.date == date
    ).delete()
    
    db.query(WorkoutSession).filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.date == date
    ).delete()
    
    db.commit()
    return None

@router.delete("/all-workout", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_workout_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete ALL workout logs and sessions for the current user.
    """
    db.query(WorkoutLog).filter(
        WorkoutLog.user_id == current_user.id
    ).delete()

    db.query(WorkoutSession).filter(
        WorkoutSession.user_id == current_user.id
    ).delete()
    
    db.commit()
    return None

@router.get("/daily-diet", status_code=status.HTTP_200_OK)
def get_daily_diet_logs(
    date: DateType = Query(default=DateType.today()),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all meal logs for the specified date (defaults to today) with calories target.
    """
    from app.models.user_profile import UserProfile
    from app.crud.meal_plan import get_current_meal_plan
    
    # Get user's calorie target: Prefer Plan Total over Profile Target
    # This ensures "Remaining" matches the actual plan generated
    calories_target = 2000 # Default fallback
    
    # 1. Try to get from active Meal Plan
    plan = get_current_meal_plan(db, current_user.id)
    if plan and plan.daily_generated_totals:
        calories_target = plan.daily_generated_totals.calories
    else:
        # 2. Fallback to Profile Target
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        if profile:
            calories_target = profile.calories
    
    meals = db.query(FoodLog).filter(
        FoodLog.user_id == current_user.id,
        FoodLog.date == date
    ).order_by(FoodLog.created_at.desc()).all()
    
    return {
        "calories_target": calories_target,
        "meals": [
            {
                "id": m.id, 
                "name": m.food_name, 
                "meal_type": m.meal_type,
                "calories": m.calories,
                "protein": m.protein,
                "carbs": m.carbs,
                "fat": m.fat,
                "created_at": m.created_at.isoformat() if m.created_at else None
            } 
            for m in meals
        ]
    }


@router.get("/daily-workout", status_code=status.HTTP_200_OK)
def get_daily_workout_logs(
    date: DateType = Query(default=DateType.today()),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all workout logs for the specified date (defaults to today) and the target calories from the plan.
    """
    # 1. Fetch Logs
    workouts = db.query(WorkoutLog).filter(
        WorkoutLog.user_id == current_user.id,
        WorkoutLog.date == date
    ).order_by(WorkoutLog.created_at.desc()).all()
    
    # 2. Fetch Target from Workout Plan
    target_calories = 0
    from app.models.workout_plan import WorkoutPlan
    from app.models.user_profile import UserProfile
    
    # Get user profile id
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    
    if profile:
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
        if plan and plan.weekly_schedule:
            # Determine day name
            day_name = date.strftime("%A") # e.g. "Monday"
            
            # Find today's schedule
            todays_plan = None
            schedule = plan.weekly_schedule
            
            # Iterate through days (day1, day2...) to find matching day_name
            for day_key, day_data in schedule.items():
                if day_data.get("day_name") == day_name:
                    todays_plan = day_data
                    break
            
            if todays_plan:
                # Sum calories from exercises
                for ex in todays_plan.get("exercises", []):
                    target_calories += (ex.get("calories_burned") or 0)
                
                # Sum calories from cardio
                for card in todays_plan.get("cardio_exercises", []):
                    target_calories += (card.get("calories_burned") or 0)

    # 3. Check for Session
    session = db.query(WorkoutSession).filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.date == date
    ).first()

    return {
        "target_calories": target_calories,
        "has_session": bool(session),
        "workouts": [
            {
                "id": w.id, 
                "name": w.exercise_name,
                "img_url": w.img_url,
                "sets": w.sets,
                "reps": w.reps,
                "weight": w.weight,
                "muscle_group": w.muscle_group,
                "notes": w.notes,
                "calories": w.calories_burned, # Mapping calories_burned to calories for frontend
                "calories_burned": w.calories_burned,
                "duration_min": w.duration_min,
                "created_at": w.created_at.isoformat() if w.created_at else None
            } 
            for w in workouts
        ]
    }


@router.get("/weekly-diet", status_code=status.HTTP_200_OK)
def get_weekly_diet_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get diet summary for the last 7 days with meal type breakdown.
    Returns:
    [
        {
            day: 'Mon',
            date: '23 Oct',
            full_date: '2023-10-23',
            calories: 1200,
            target: 2000,
            calories_breakfast: 400,
            calories_lunch: 600,
            calories_dinner: 200,
            calories_snack: 0,
            calories_other: 0
        },
        ...
    ]
    """
    from datetime import timedelta
    from sqlalchemy import func, case
    from app.models.user_profile import UserProfile
    from app.crud.meal_plan import get_current_meal_plan
    from app.models.meal_plan_history import MealPlanHistory

    # 1. Determine Date Range (Last 7 days including today)
    today = DateType.today()
    start_date = today - timedelta(days=6)
    
    # 2. Fetch Historical Plans (Optimized)
    # Get all history entries created before or during the week range
    # We need enough history to find the active plan for the start_date
    history_records = db.query(MealPlanHistory).filter(
        MealPlanHistory.user_profile_id == UserProfile.id, # Join needed below or separate query
        UserProfile.user_id == current_user.id
    ).order_by(MealPlanHistory.created_at.desc()).all()
    
    # Helper to clean/parse nutrients from snapshot
    def get_calories_from_snapshot(snapshot):
        if not snapshot: return 0
        total = 0
        for item in snapshot:
            # Item might be dict (if loaded from JSON)
            if isinstance(item, dict):
                nuts = item.get('nutrients', {})
                # nutrients might be a dict or object depending on serialization
                if isinstance(nuts, dict):
                    p = float(nuts.get('p', 0))
                    c = float(nuts.get('c', 0))
                    f = float(nuts.get('f', 0))
                    total += (p * 4) + (c * 4) + (f * 9)
        return int(total)

    # Pre-calculate targets for history entries
    history_targets = [] 
    for h in history_records:
        history_targets.append({
            "date": h.created_at.date(),
            "calories": get_calories_from_snapshot(h.meal_plan_snapshot)
        })

    # Fallback Profile Target
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    profile_target = profile.calories if profile else 2000

    # 3. Query Logs - Aggregate by Date AND Meal Type
    # We want to pivot or just sum conditionally
    
    # Conditional aggregation is cleaner
    results = db.query(
        FoodLog.date,
        func.sum(FoodLog.calories).label('total_calories'),
        func.sum(case((FoodLog.meal_type.ilike('breakfast'), FoodLog.calories), else_=0)).label('breakfast'),
        func.sum(case((FoodLog.meal_type.ilike('lunch'), FoodLog.calories), else_=0)).label('lunch'),
        func.sum(case((FoodLog.meal_type.ilike('dinner'), FoodLog.calories), else_=0)).label('dinner'),
        func.sum(case((FoodLog.meal_type.ilike('snack%'), FoodLog.calories), else_=0)).label('snack')
    ).filter(
        FoodLog.user_id == current_user.id,
        FoodLog.date >= start_date,
        FoodLog.date <= today
    ).group_by(FoodLog.date).all()


    # Convert to dictionary for easy lookup by date
    # Each entry in map: { '2023-10-23': { total: 1000, bk: 300, ... } }
    data_map = {}
    for r in results:
        data_map[r.date] = {
            "total": r.total_calories or 0,
            "breakfast": r.breakfast or 0,
            "lunch": r.lunch or 0,
            "dinner": r.dinner or 0,
            "snack": r.snack or 0
        }

    # 4. Build Response for Last 7 Days (ensuring all days are present)
    weekly_data = []
    
    # Iterate from start_date to today
    current_day = start_date
    while current_day <= today:
        day_stats = data_map.get(current_day, {})
        
        # Calculate 'other' as remainder (total - explicit parts)
        total = float(day_stats.get("total", 0))
        bk = float(day_stats.get("breakfast", 0))
        ln = float(day_stats.get("lunch", 0))
        dn = float(day_stats.get("dinner", 0))
        sn = float(day_stats.get("snack", 0))
        
        # Sometimes 'meal_type' might be null or different string, catch those in 'other'
        other = total - (bk + ln + dn + sn)
        if other < 0: other = 0 # Floating point safety

        # Calculate Daily Target based on History
        # Find the most recent plan created ON or BEFORE this current_day
        day_target = profile_target # Default fallback
        
        found_history = False
        for h in history_targets:
            if h["date"] <= current_day:
                day_target = h["calories"]
                found_history = True
                break
        
        weekly_data.append({
            "day": current_day.strftime("%a"), # Mon, Tue...
            "date": current_day.strftime("%d %b"), # 23 Oct
            "full_date": current_day.isoformat(), # 2023-10-23
            "calories": int(total),
            "target": int(day_target),
            "calories_breakfast": int(bk),
            "calories_lunch": int(ln),
            "calories_dinner": int(dn),
            "calories_snack": int(sn),
            "calories_other": int(other)
        })
        current_day += timedelta(days=1)
    
    return weekly_data


@router.get("/weekly-workout", status_code=status.HTTP_200_OK)
def get_weekly_workout_overview(
    week_offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get workout summary for the CURRENT WEEK (Monday to Sunday).
    Returns:
    {
        "total_calories": 2270,
        "days_active": 5,
        "total_minutes": 330,
        "avg_duration": 66,
        "expected_calories": 2500,  # Sum from Plan
        "chart_data": [
            { "day": "Mon", "calories": 450 },
            ...
        ]
    }
    """
    from datetime import timedelta
    from sqlalchemy import func
    from app.models.workout_plan import WorkoutPlan
    from app.models.user_profile import UserProfile

    # 1. Determine Week Range (Monday to Sunday) with Offset
    today = DateType.today()
    # weekday(): Mon=0, Sun=6
    current_week_start = today - timedelta(days=today.weekday())
    
    # Apply offset
    start_of_week = current_week_start + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)

    # 2. Query Logs for this week
    logs = db.query(
        WorkoutLog.date,
        func.sum(WorkoutLog.calories_burned).label('daily_calories'),
        func.sum(WorkoutLog.duration_min).label('daily_duration')
    ).filter(
        WorkoutLog.user_id == current_user.id,
        WorkoutLog.date >= start_of_week,
        WorkoutLog.date <= end_of_week
    ).group_by(WorkoutLog.date).all()

    # 2b. Query Sessions for Duration (New Logic)
    sessions = db.query(
        WorkoutSession.date,
        WorkoutSession.duration_minutes
    ).filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.date >= start_of_week,
        WorkoutSession.date <= end_of_week
    ).all()

    # 3. Process Data
    # Map by date string for easy lookup
    data_map = {log.date: log for log in logs}
    session_map = {s.date: s.duration_minutes for s in sessions}
    
    total_calories = 0
    total_minutes = 0
    days_with_activity = 0
    
    chart_data = []
    
    # Iterate Mon -> Sun
    current = start_of_week
    while current <= end_of_week:
        log = data_map.get(current)
        
        cal = float(log.daily_calories) if log and log.daily_calories else 0
        
        # Duration: Prefer Session > Sum of Logs
        session_dur = session_map.get(current, 0)
        log_dur_sum = int(log.daily_duration) if log and log.daily_duration else 0
        
        dur = session_dur if session_dur > 0 else log_dur_sum
        
        total_calories += cal
        total_minutes += dur
        
        # "Active Day" loose definition: Any activity
        if cal > 0 or dur > 0:
            days_with_activity += 1
            
        chart_data.append({
            "day": current.strftime("%a"), # Mon, Tue
            "date_label": current.strftime("%d %b"), # 23 Oct
            "calories": int(cal) # For chart
        })
        
        current += timedelta(days=1)
        
    avg_duration = int(total_minutes / days_with_activity) if days_with_activity > 0 else 0
    
    # 4. Calculate Expected Calories from Plan
    expected_calories = 0
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if profile:
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
        if plan and plan.weekly_schedule:
             for day_data in plan.weekly_schedule.values():
                 # Sum up calories for all scheduled days
                 # Logic matches get_daily_workout_logs summation
                 day_cals = 0
                 for ex in day_data.get("exercises", []):
                     day_cals += (ex.get("calories_burned") or 0)
                 for card in day_data.get("cardio_exercises", []):
                     day_cals += (card.get("calories_burned") or 0)
                 
                 expected_calories += day_cals

    return {
        "total_calories": int(total_calories),
        "days_active": days_with_activity,
        "total_minutes": total_minutes,
        "avg_duration": avg_duration,
        "expected_calories": int(expected_calories),
        "chart_data": chart_data
    }


@router.get("/weekly-goals", status_code=status.HTTP_200_OK)
def get_weekly_goals(
    week_offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get weekly goal progress for Workout (vs Plan) and Diet (vs 7 days).
    """
    from sqlalchemy import func
    from datetime import timedelta
    from app.models.workout_plan import WorkoutPlan
    from app.models.user_profile import UserProfile

    # 1. Determine Week Range with Offset
    today = DateType.today()
    current_week_start = today - timedelta(days=today.weekday())
    
    start_of_week = current_week_start + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)

    # 2. Get Targets
    
    # Workout Target: Dynamic based on Plan
    workout_target = 7 # Default legacy
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if profile:
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
        if plan and plan.weekly_schedule:
            # Count scheduled days
            count = 0
            for day_data in plan.weekly_schedule.values():
                is_rest = day_data.get("is_rest", False)
                # Ensure it actually has exercises
                has_content = (day_data.get("exercises") and len(day_data.get("exercises")) > 0) or \
                              (day_data.get("cardio_exercises") and len(day_data.get("cardio_exercises")) > 0)
                
                if not is_rest and has_content:
                    count += 1
            
            if count > 0:
                workout_target = count
        
    diet_target = 7  # Always 7 days/week

    # 3. Get Current Progress (Unique Days)
    # Workout
    workout_days_count = db.query(func.count(func.distinct(WorkoutLog.date))).filter(
        WorkoutLog.user_id == current_user.id,
        WorkoutLog.date >= start_of_week,
        WorkoutLog.date <= end_of_week
    ).scalar() or 0

    # Diet
    diet_days_count = db.query(func.count(func.distinct(FoodLog.date))).filter(
        FoodLog.user_id == current_user.id,
        FoodLog.date >= start_of_week,
        FoodLog.date <= end_of_week
    ).scalar() or 0

    # 4. Calculate Percentage
    # Cap at 100% for individual adherence before averaging, or average then cap?
    # Simple average of adherence.
    
    w_adherence = min(workout_days_count / workout_target, 1.0) if workout_target > 0 else 0
    d_adherence = min(diet_days_count / diet_target, 1.0)
    
    overall_percentage = int(((w_adherence + d_adherence) / 2) * 100)

    return {
        "workout": {
            "current": workout_days_count,
            "target": workout_target
        },
        "diet": {
            "current": diet_days_count,
            "target": diet_target
        },
        "overall_percentage": overall_percentage
    }


@router.get("/workout-calendar", status_code=status.HTTP_200_OK)
def get_workout_calendar(
    week_offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get 7-day calendar view for the requested week offset (0 = current week).
    Supports cyclic 8-week program logic.
    """
    from datetime import timedelta
    from app.models.workout_plan import WorkoutPlan
    
    # 1. Get User's Plan
    profile = current_user.profile
    
    # Handle potential list return from relationship (InstrumentedList)
    if isinstance(profile, list):
        profile = profile[0] if profile else None
        
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Workout Plan not found. Please generate one first.")
        
    # 2. Determine "Current Cyclic Week"
    # Plan Duration (default 8 weeks)
    plan_duration = plan.duration_weeks or 8
    
    # Calculate effective start date (Monday of the creation week)
    # If no created_at, assume today
    raw_start_date = plan.created_at.date() if plan.created_at else DateType.today()
    # Align to Monday: Monday=0, Sunday=6. Subtract weekday() days.
    # e.g. Wed (2) -> Subtract 2 days -> Mon.
    start_date = raw_start_date - timedelta(days=raw_start_date.weekday())
    
    today = DateType.today() 
    
    # Weeks elapsed since start
    weeks_elapsed = (today - start_date).days // 7
    
    # Current Cycle Week (0 to plan_duration-1)
    current_cycle_week_index = weeks_elapsed % plan_duration
    
    # Apply requested offset
    target_week_index = current_cycle_week_index + week_offset
    
    # Let's simplify: Anchor to "Current Real Week"
    current_week_start = today - timedelta(days=today.weekday()) # This Monday
    
    # Target Week Start
    target_week_start = current_week_start + timedelta(weeks=week_offset)
    target_week_end = target_week_start + timedelta(days=6)
    
    # Determine which Plan Week Template to use for this Target Week?
    weeks_diff_from_start = (target_week_start - start_date).days // 7
    # Ensure non-negative modulo if creation is in future (unlikely but safe)
    if weeks_diff_from_start < 0:
         weeks_diff_from_start = 0
         
    template_week_num = (weeks_diff_from_start % plan_duration) + 1 # 1-based (Week 1..8)
    
    # Format Range Label for UI
    date_range_p = f"{target_week_start.strftime('%b %d')} - {target_week_end.strftime('%b %d')}"
    
    # 3. Get Logs for the Target Week
    logs = db.query(WorkoutLog).filter(
        WorkoutLog.user_id == current_user.id,
        WorkoutLog.date >= target_week_start,
        WorkoutLog.date <= target_week_end
    ).all()
    
    # Map logs by date -> set of exercise names for easy lookup
    logs_by_date = {}
    for log in logs:
        if log.date not in logs_by_date:
            logs_by_date[log.date] = set()
        if log.exercise_name:
            logs_by_date[log.date].add(log.exercise_name.lower().strip())

    # 3b. Get Sessions for Duration
    sessions = db.query(WorkoutSession).filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.date >= target_week_start,
        WorkoutSession.date <= target_week_end
    ).all()
    
    session_map = {s.date: s.duration_minutes for s in sessions}
    
    # 4. Build 7-Day View
    days_data = []
    
    # Parse Schedule
    schedule_map = {}
    try:
        if isinstance(plan.weekly_schedule, dict):
            for k, v in plan.weekly_schedule.items():
                if isinstance(v, dict) and "day_name" in v:
                    schedule_map[v["day_name"]] = v
    except Exception as e:
        print(f"Error parsing weekly_schedule: {e}")
                
    # Day Names in order
    week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    current_d = target_week_start
    for i in range(7):
        day_name = week_days[i]
        date_str = current_d.strftime("%Y-%m-%d")
        
        # Get Template
        template = schedule_map.get(day_name, {})
        
        # Get Logs for this specific date
        logged_exercises_set = logs_by_date.get(current_d, set())
        
        is_rest = template.get("is_rest", False)
        if not is_rest and not template.get("exercises") and not template.get("cardio_exercises"):
            is_rest = True
            
        # Determine "Type/Split" for Coloring
        w_type = template.get("split") or template.get("focus") or ("Rest" if is_rest else "Workout")
        
        # Determine "Title"
        w_title = template.get("workout_name") or w_type
        
        # Exercises list for preview & status calculation
        planned_exercises = []
        if template.get("exercises"):
            # Check for 'exercise' key (common) or 'exercise_name'
            planned_exercises.extend([ex.get("exercise") or ex.get("exercise_name") for ex in template.get("exercises") if (ex.get("exercise") or ex.get("exercise_name"))])
        if template.get("cardio_exercises"):
             planned_exercises.extend([ex.get("exercise") for ex in template.get("cardio_exercises") if ex.get("exercise")])
             
        # Calculate Remaining
        total_exercises = len(planned_exercises)
        remaining_count = 0
        remaining_exercise_names = []
        
        if not is_rest and total_exercises > 0:
            for ex in planned_exercises:
                # Simple loose matching: check if planned name is in logged set
                # In production, might need fuzzy matching or ID matching
                if ex and ex.lower().strip() not in logged_exercises_set:
                    remaining_count += 1
                    remaining_exercise_names.append(ex)
        
        # Determine Completion Status
        # If it's a rest day, it's "completed" if it's in the past? No, usually just "Rest".
        # If workout day:
        # - Completed if total > 0 and remaining == 0
        is_completed = (not is_rest and total_exercises > 0 and remaining_count == 0)
        
        # Duration info
        est_min = template.get("estimated_duration", 45) # Default
        if "session_duration_min" in template:
             est_min = template["session_duration_min"]
        
        # Override with actual if available
        actual_dur = session_map.get(current_d)
        display_duration = actual_dur if actual_dur else est_min
        
        days_data.append({
            "date": date_str, 
            "day_name": current_d.strftime("%a"), 
            "full_day_name": day_name,
            "date_label": current_d.strftime("%b %d"), # e.g. "Feb 12" 
            "type": w_type,      
            "title": w_title,    
            "exercises": planned_exercises,
            "duration": display_duration,
            "is_actual_duration": bool(actual_dur),
            "completed": is_completed,
            "is_rest": is_rest,
            "remaining_exercises": remaining_count,
            "remaining_exercise_names": remaining_exercise_names,
            "total_exercises": total_exercises
        })
        
        current_d += timedelta(days=1)
        
    return {
        "current_week": template_week_num, # 1 to 8
        "total_weeks": plan_duration,
        "week_offset": week_offset,
        "date_range": date_range_p, # "Feb 03 - Feb 09"
        "days": days_data
    }
