
import sys
import os
from sqlalchemy import text

# Add backend to path
import sys, os; from pathlib import Path; sys.path.insert(0, str([p for p in Path(__file__).resolve().parents if (p / 'backend').exists()][0] / 'backend')) # modified

from app.database import SessionLocal

def show_logs():
    db = SessionLocal()
    try:
        print("\n--- Recent Workout Logs ---")
        result = db.execute(text("""
            SELECT id, date, exercise_name, sets, reps 
            FROM workout_logs 
            ORDER BY date DESC, id DESC
            LIMIT 20
        """))
        rows = result.fetchall()
        
        if not rows:
            print("No workout logs found.")
        else:
            for row in rows:
                print(f"ID: {row[0]} | Date: {row[1]} | Exercise: {row[2]} | Sets: {row[3]} | Reps: {row[4]}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    show_logs()
