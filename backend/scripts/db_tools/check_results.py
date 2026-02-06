import sys
import os
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.database import SessionLocal
from app.models.meal_plan import MealPlan

def check_plans():
    db = SessionLocal()
    try:
        count = db.query(MealPlan).count()
        print(f"Meal Plans Count: {count}")
        
        if count > 0:
            plans = db.query(MealPlan).limit(5).all()
            for p in plans:
                print(f"Plan: {p.label} - {p.dish_name} (Veg: {p.is_veg})")
    finally:
        db.close()

if __name__ == "__main__":
    check_plans()
