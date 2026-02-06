import os
import platform
from celery import Celery

# Get Redis URL from env or default
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Determine pool type based on OS (macOS fork is unsafe with native extensions)
# Using 'solo' on macOS avoids fork-related SIGSEGV crashes
if platform.system() == "Darwin":
    pool_type = "solo"
else:
    pool_type = "prefork"

# Initialize Celery
celery_app = Celery(
    "fitness_tracker",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks.scheduler"] # Expected location of tasks
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Fix for macOS SIGSEGV: use spawn pool instead of fork
    worker_pool=pool_type,
    worker_prefetch_multiplier=1,  # Better for spawn pool
    beat_schedule_filename="celery_beat_data/celerybeat-schedule", # Keep root clean
)

# Optional: Beat Schedule can be defined here if static
# But we will likely use dynamic or file-based scheduling in tasks/scheduler.py
