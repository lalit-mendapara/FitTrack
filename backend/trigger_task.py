import sys
import os
sys.path.append(os.getcwd())
from app.tasks.scheduler import generate_plan_for_user

if len(sys.argv) > 1:
    user_id = int(sys.argv[1])
else:
    user_id = 42

print(f"Triggering generate_plan_for_user for user {user_id}...")
try:
    task = generate_plan_for_user.delay(user_id)
    print(f"Task dispatched successfully. Task ID: {task.id}")
    print("Check 'docker logs -f diet_planner_celery' to see execution.")
except Exception as e:
    print(f"Error dispatching task: {e}")
