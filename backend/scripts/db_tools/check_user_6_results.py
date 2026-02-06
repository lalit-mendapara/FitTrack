import sys
import os
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.database import SessionLocal
from app.models.meal_plan import MealPlan

def check_plans_user_6():
    db = SessionLocal()
    try:
        count = db.query(MealPlan).filter(MealPlan.user_profile_id == 4).count()
        print(f"Meal Plans for Profile 4 (User 6): {count}")
        
        if count > 0:
            plans = db.query(MealPlan).filter(MealPlan.user_profile_id == 4).all()
            for p in plans:
                print(f"Plan: {p.label} - {p.dish_name}")
    finally:
        db.close()

if __name__ == "__main__":
    check_plans_user_6()
