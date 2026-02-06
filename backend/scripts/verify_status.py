
import sys
import os
from datetime import date, timedelta
from sqlalchemy import text

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.workout_plan import WorkoutPlan
from app.models.tracking import WorkoutLog

def verify_logic():
    db = SessionLocal()
    try:
        # 1. Get Current User's Plan (Assuming single user scenario or getting latest)
        # We'll just grab the latest plan
        plan = db.query(WorkoutPlan).order_by(WorkoutPlan.created_at.desc()).first()
        if not plan:
            print("No workout plan found.")
            return

        print(f"Plan ID: {plan.id}, Duration: {plan.duration_weeks} weeks")
        weekly_schedule = plan.weekly_schedule
        print(f"Weekly Schedule Type: {type(weekly_schedule)}")
        print(f"Keys: {weekly_schedule.keys()}")
        
        # Adjust logic to get the list
        schedule_list = []
        weekly_schedule = list(weekly_schedule.values())
        if weekly_schedule:
             print(f"Sample Day Plan: {weekly_schedule[0]}")




        
        # 2. Check last 7 days Logs
        today = date.today()
        start_date = today - timedelta(days=7)
        
        print(f"\nChecking logs from {start_date} to {today}...\n")
        
        for i in range(8):
            check_date = start_date + timedelta(days=i)
            day_logs = db.query(WorkoutLog).filter(WorkoutLog.date == check_date).all()
            logged_count = len(day_logs)
            
            # Determine expected exercises for this day (Cyclic Logic simplified)
            # Find the template day for this date
            # Monday = 0
            day_name_map = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}
            day_name = day_name_map[check_date.weekday()]
            
            # Find day in schedule
            day_plan = next((d for d in weekly_schedule if d.get('day') == day_name), None)
            
            if not day_plan:
                print(f"[{check_date}] {day_name}: No plan found.")
                continue
                
            is_rest = day_plan.get('is_rest', False)
            if is_rest:
                print(f"[{check_date}] {day_name}: Rest Day")
                continue
                
            # Count expected
            exercises = day_plan.get('exercises', [])
            cardio = day_plan.get('cardio_exercises', [])
            total_expected = len(exercises) + len(cardio)
            
            # Logic Check
            status = "UNKNOWN"
            if logged_count == 0:
                status = "SKIPPED (Red)"
            elif logged_count < total_expected:
                status = "INCOMPLETE (Yellow)"
            else:
                status = "COMPLETED (Green)"
                
            print(f"[{check_date}] {day_name}: {status}") 
            print(f"   Logged: {logged_count}/{total_expected}")
            if logged_count > 0 and logged_count < total_expected:
                print("   !!! THIS SHOULD SHOW YELLOW ON UI !!!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_logic()
