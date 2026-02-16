from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.workout_plan import WorkoutPlanRequest, WorkoutPlanResponse
from app.services.workout_service import generate_workout_plan
from app.api.auth import get_current_user
import sys

# Langfuse tracing
observe = lambda *args, **kwargs: (lambda f: f)  # No-op decorator fallback
if sys.version_info < (3, 14):
    try:
        from langfuse import observe
    except ImportError:
        pass

router = APIRouter(
    prefix="/workout-plans",
    tags=["Workout Plans"]
)

from app.models.tracking import WorkoutLog

@router.post("/generate", response_model=None)
@observe(name="generate_workout_plan")
def generate_plan_endpoint(
    request: WorkoutPlanRequest, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Generate a personalized workout plan based on user profile and preferences.
    """
    try:
        # Inject user_id from token
        print(f"[DEBUG] Generate Workout - Current User ID: {current_user.id}")
        request.workout_request.user_id = current_user.id
        print(f"[DEBUG] Request User ID set to: {request.workout_request.user_id}")
        
        print(f"[DEBUG] Request User ID set to: {request.workout_request.user_id}")
        
        # Pass the inner data object to the CRUD function
        plan = generate_workout_plan(db, request.workout_request)
        
        if not plan:
            raise HTTPException(status_code=500, detail="Failed to generate workout plan")
            
        return plan
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Unhandled Exception: {e}")
        # Return generic error message to client, log the specific error
        raise HTTPException(status_code=500, detail="Failed to generate workout plan")

@router.get("/current", response_model=WorkoutPlanResponse)
def get_current_workout(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    from app.crud.workout_plan import get_current_workout_plan
    from app.services.feast_mode_manager import FeastModeManager
    
    plan = get_current_workout_plan(db, current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="Workout plan not found")
        
    # Inject Feast Mode Workout if active
    try:
        feast_manager = FeastModeManager(db)
        # We need to modify the plan object or its dictionary representation
        # Pydantic models from ORM objects are tricky to mutate in-place if returning the ORM object directly.
        # But FastAPI handles ORM -> Response Model conversion.
        # We can update the 'weekly_schedule' attribute of the ORM object temporarily (it won't persist unless committed)
        # or better, convert to dict and update.
        
        # However, plan is an ORM object. `plan.weekly_schedule` is a JSON field (dict).
        # We can update it.
        if plan.weekly_schedule:
             updated_schedule = feast_manager.inject_feast_workout_into_plan(current_user.id, plan.weekly_schedule)
             # Important: We must not commit this change to DB, just return it.
             # Modifying the ORM object's attribute effectively changes what's returned.
             plan.weekly_schedule = updated_schedule
             
    except Exception as e:
        print(f"Failed to inject feast workout: {e}")
        # non-blocking
        
    return plan
