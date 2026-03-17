"""
Async API endpoints for workout plan generation using Celery tasks.
Provides task_id based polling instead of blocking HTTP requests.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.workout_plan import WorkoutPlanRequest, WorkoutPlanResponse
from app.api.auth import get_current_user
from celery.result import AsyncResult
from app.celery_app import celery_app
from pydantic import BaseModel
from typing import Optional
import sys

# Langfuse tracing
observe = lambda *args, **kwargs: (lambda f: f)
if sys.version_info < (3, 14):
    try:
        from langfuse import observe
    except ImportError:
        pass

router = APIRouter(
    prefix="/workout-plans",
    tags=["Workout Plans (Async)"]
)


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # PENDING, PROCESSING, SUCCESS, FAILURE
    progress: Optional[int] = None
    message: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


@router.post("/generate-async", response_model=TaskResponse)
@observe(name="generate_workout_plan_async_endpoint")
def generate_plan_async_endpoint(
    request: WorkoutPlanRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Initiate async workout plan generation.
    Returns task_id immediately for polling.
    
    Frontend should poll /workout-plans/status/{task_id} for completion.
    """
    try:
        # Inject user_id from token
        request.workout_request.user_id = current_user.id
        
        # Convert to dict for Celery serialization
        request_dict = request.workout_request.dict()
        
        # Launch Celery task
        from app.tasks.workout_tasks import generate_workout_plan_async
        task = generate_workout_plan_async.delay(request_dict)
        
        return TaskResponse(
            task_id=task.id,
            status="PENDING",
            message="Workout plan generation started. Poll /workout-plans/status/{task_id} for progress."
        )
        
    except Exception as e:
        print(f"[ERROR] Failed to start async task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start generation: {str(e)}")


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    """
    Poll task status by task_id.
    
    Status values:
    - PENDING: Task queued, not started
    - PROCESSING: Task running (check progress field)
    - SUCCESS: Task completed (check result field)
    - FAILURE: Task failed (check error field)
    """
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        if task_result.state == 'PENDING':
            return TaskStatusResponse(
                task_id=task_id,
                status="PENDING",
                message="Task is queued and waiting to start"
            )
        
        elif task_result.state == 'PROCESSING':
            # Get progress from task meta
            meta = task_result.info or {}
            return TaskStatusResponse(
                task_id=task_id,
                status="PROCESSING",
                progress=meta.get('progress', 0),
                message=meta.get('status', 'Generating workout plan...')
            )
        
        elif task_result.state == 'SUCCESS':
            result = task_result.result
            
            if result and result.get('status') == 'success':
                return TaskStatusResponse(
                    task_id=task_id,
                    status="SUCCESS",
                    progress=100,
                    message="Workout plan generated successfully",
                    result=result.get('plan')
                )
            else:
                # Task completed but generation failed
                return TaskStatusResponse(
                    task_id=task_id,
                    status="FAILURE",
                    error=result.get('error', 'Unknown error')
                )
        
        elif task_result.state == 'FAILURE':
            return TaskStatusResponse(
                task_id=task_id,
                status="FAILURE",
                error=str(task_result.info)
            )
        
        else:
            # Unknown state
            return TaskStatusResponse(
                task_id=task_id,
                status=task_result.state,
                message=f"Task in state: {task_result.state}"
            )
    
    except Exception as e:
        print(f"[ERROR] Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.delete("/cancel/{task_id}")
def cancel_task(task_id: str):
    """
    Cancel a running task.
    Note: Task may not stop immediately if already processing.
    """
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        task_result.revoke(terminate=True)
        
        return {
            "task_id": task_id,
            "status": "CANCELLED",
            "message": "Task cancellation requested"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")
