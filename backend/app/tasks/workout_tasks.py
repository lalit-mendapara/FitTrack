"""
Celery tasks for async workout plan generation
"""
from celery import Task
from app.celery_app import celery_app
from app.database import SessionLocal
from app.schemas.workout_plan import WorkoutPlanRequestData
import traceback


class DatabaseTask(Task):
    """Base task with database session management"""
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(bind=True, base=DatabaseTask, name="tasks.generate_workout_plan_async")
def generate_workout_plan_async(self, request_data_dict: dict):
    """
    Async Celery task for workout plan generation.
    
    Args:
        request_data_dict: Serialized WorkoutPlanRequestData
        
    Returns:
        dict: {
            "status": "success" | "error",
            "plan": {...} | None,
            "error": str | None
        }
    """
    from app.services.workout_service import generate_workout_plan_optimized
    from app.schemas.workout_plan import WorkoutPlanRequestData
    
    try:
        # Update task state to PROCESSING
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Generating workout plan...', 'progress': 10}
        )
        
        # Reconstruct request object
        request_data = WorkoutPlanRequestData(**request_data_dict)
        
        # Call optimized generation service
        plan = generate_workout_plan_optimized(self.db, request_data, task=self)
        
        if not plan:
            return {
                "status": "error",
                "plan": None,
                "error": "Failed to generate workout plan"
            }
        
        # Convert to dict for JSON serialization
        from app.schemas.workout_plan import WorkoutPlanResponse
        plan_dict = WorkoutPlanResponse.from_orm(plan).dict()
        
        return {
            "status": "success",
            "plan": plan_dict,
            "error": None
        }
        
    except Exception as e:
        error_msg = f"Workout generation failed: {str(e)}"
        print(f"[CELERY ERROR] {error_msg}")
        traceback.print_exc()
        
        return {
            "status": "error",
            "plan": None,
            "error": error_msg
        }
