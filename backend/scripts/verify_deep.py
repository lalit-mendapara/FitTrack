
import sys
import os
from datetime import date
from sqlalchemy import text

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.workout_plan import WorkoutPlan
from app.models.tracking import WorkoutLog

def verify_deep():
    db = SessionLocal()
    try:
        # 1. Get Plan
        plan = db.query(WorkoutPlan).order_by(WorkoutPlan.created_at.desc()).first()
        if not plan:
            print("No plan.")
            return

        weekly_schedule = plan.weekly_schedule
        if isinstance(weekly_schedule, dict):
            weekly_schedule = list(weekly_schedule.values())

        # 2. Get Today's Day Name
        today = date.today()
        # Monday=0
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_name = day_names[today.weekday()]
        
        print(f"\n--- Checking for TODAY: {today} ({day_name}) ---")
        
        # 3. Find Today's Template
        day_template = next((d for d in weekly_schedule if d.get('day_name') == day_name), None)
        if not day_template:
            print("No template found for today!")
            return

        # 4. Extract Planned Names
        planned_names = []
        if day_template.get('exercises'):
            planned_names.extend([ex.get('exercise') for ex in day_template.get('exercises') if ex.get('exercise')])
        if day_template.get('cardio_exercises'):
             planned_names.extend([ex.get('exercise') for ex in day_template.get('cardio_exercises') if ex.get('exercise')])
             
        print(f"Planned ({len(planned_names)}): {planned_names}")
        
        # 5. Get Logs
        logs = db.query(WorkoutLog).filter(WorkoutLog.date == today).all()
        logged_names = [log.exercise_name for log in logs]
        print(f"Logged ({len(logged_names)}): {logged_names}")
        
        # 6. Compare (Simulate Backend Logic)
        logged_set = {n.lower().strip() for n in logged_names if n}
        
        remaining = 0
        matches = []
        mismatches = []
        
        for p in planned_names:
            p_clean = p.lower().strip()
            if p_clean in logged_set:
                matches.append(p)
            else:
                remaining += 1
                mismatches.append(p)
                
        total = len(planned_names)
        
        print("\n--- Logic Results ---")
        print(f"Total: {total}")
        print(f"Remaining: {remaining}")
        print(f"Matches: {matches}")
        print(f"NOT Logged: {mismatches}")
        
        has_started = remaining < total
        print(f"Has Started? {has_started}")
        print(f"UI Should Show: {'INCOMPLETE (Yellow)' if has_started else 'NOT STARTED'}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_deep()
