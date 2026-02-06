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
        
        # 1. Generate Plan
        # We assume this function saves to DB internally
        meal_service.generate_meal_plan(db, user_id)
        
        # 2. Create Notification
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
@celery_app.task
def generate_daily_plans_scheduler():
    """
    Beat task: Runs every hour. 
    Finds users where local time is 5:00 AM (± buffer) and triggers worker task.
    """
    db: Session = SessionLocal()
    try:
        # Get all profiles
        profiles = db.query(UserProfile).all()
        
        triggered_count = 0
        
        for profile in profiles:
            user_tz_str = profile.timezone or "UTC"
            try:
                tz = pytz.timezone(user_tz_str)
                user_now = datetime.now(tz)
                
                # Check if it is 5 AM (e.g., between 5:00 and 5:59)
                # Since we run hourly, checking 'hour == 5' is sufficient.
                if user_now.hour == 9:
                    generate_plan_for_user.delay(profile.user_id)
                    triggered_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing timezone for user {profile.user_id}: {e}")
                
        logger.info(f"Daily Plan Scheduler ran. Triggered {triggered_count} tasks.")
        
    finally:
        db.close()

# --- SCHEDULE CONFIG ---
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'check-hourly-9:45am': {
        'task': 'app.tasks.scheduler.generate_daily_plans_scheduler',
        'schedule': crontab(minute=59)  # Run every hour
    },
}
