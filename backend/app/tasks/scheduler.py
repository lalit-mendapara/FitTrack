from app.celery_app import celery_app
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user_profile import UserProfile
from app.models.notification import Notification
from app.services import meal_service
from datetime import datetime
import pytz
import logging
import sys

logger = logging.getLogger(__name__)

# Langfuse tracing
observe = lambda *args, **kwargs: (lambda f: f)  # No-op decorator fallback
if sys.version_info < (3, 14):
    try:
        from langfuse import observe
    except ImportError:
        pass

# --- WORKER TASK ---
@celery_app.task
@observe(name="celery_generate_plan_for_user")
def generate_plan_for_user(user_id: int):
    """
    Worker task: Generates the plan for a specific user.
    """
    db: Session = SessionLocal()
    try:
        logger.info(f"Generating daily plan for user {user_id}")
        
        # 1. Generate Plan with History-Based Variety
        # Uses last 8 plans to ensure no dish repetition
        meal_service.regenerate_meal_plan(db, user_id)
        
        # 2. Feast Mode Agent: Auto-apply LLM adjustment if in banking phase
        try:
            from app.services.social_event_service import get_active_event
            from app.services.stats_service import StatsService
            from datetime import date as date_type
            
            today = date_type.today()
            event = get_active_event(db, user_id, today)
            
            if event and event.start_date <= today < event.event_date:
                # User is in banking phase, apply smart adjustment
                stats = StatsService(db)
                input_profile = stats.get_user_profile(user_id)
                effective_target = input_profile["caloric_target"]
                
                logger.info(f"[FeastAgent] Auto-adjusting for banking phase. Target: {effective_target}")
                meal_service.adjust_meals_with_llm(db, user_id, effective_target, [])
        except Exception as e:
            logger.error(f"[FeastAgent] Auto-adjustment failed for user {user_id}: {e}")
        
        # 3. Create Notification
        notif = Notification(
            user_id=user_id,
            message="Good Morning! Your diet plan for today is ready.",
            type="plan_ready"
        )
        db.add(notif)
        db.commit()
        
        logger.info(f"Plan generated and notification sent for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error generating plan for user {user_id}: {e}")
        # Optionally retry here or let Celery handle retries via task config
    finally:
        db.close()

# --- BEAT SCHEDULER TASK ---
from app.crud import meal_plan as crud_meal_plan

@celery_app.task
def generate_daily_plans_scheduler():
    """
    Beat task: Runs every hour. 
    Finds users where local time is 5:00 AM (± buffer) and triggers worker task.
    Skips if a plan for today already exists.
    """
    db: Session = SessionLocal()
    try:
        # Get all profiles
        profiles = db.query(UserProfile).all()
        
        triggered_count = 0
        skipped_count = 0
        
        for profile in profiles:
            user_tz_str = profile.timezone or "UTC"
            try:
                tz = pytz.timezone(user_tz_str)
                user_now = datetime.now(tz)
                
                # Check if it is 5 AM or later (Catch-up logic)
                if user_now.hour >= 5:
                    
                    # IDEMPOTENCY CHECK:
                    # Check if user already has a plan for TODAY
                    current_plan = crud_meal_plan.get_current_meal_plan(db, profile.user_id)
                    if current_plan and current_plan.created_at:
                        # Convert DB time (UTC) to User TZ
                        # Note: SQLAlchemy datetime is usually naive, assumed UTC
                        created_utc = current_plan.created_at
                        if created_utc.tzinfo is None:
                            created_utc = created_utc.replace(tzinfo=pytz.utc)
                            
                        # Convert to user local time
                        created_local = created_utc.astimezone(tz)
                        
                        # Compare dates
                        if created_local.date() == user_now.date():
                            logger.info(f"User {profile.user_id} already has a plan for today ({user_now.date()}). Skipping.")
                            skipped_count += 1
                            continue
                    
                    generate_plan_for_user.delay(profile.user_id)
                    triggered_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing timezone for user {profile.user_id}: {e}")
                
        logger.info(f"Daily Plan Scheduler ran. Triggered {triggered_count} tasks. Skipped {skipped_count} (already exist).")
        
    finally:
        db.close()

# --- SCHEDULE CONFIG ---
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'check-hourly-5am': {
        'task': 'app.tasks.scheduler.generate_daily_plans_scheduler',
        'schedule': crontab(minute=00)  # Run at top of every hour
    },
}
