import sys
import os
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.database import SessionLocal

def inspect_values():
    db = SessionLocal()
    try:
        diet_types = db.execute(text("SELECT DISTINCT diet_type FROM food_items")).fetchall()
        print(f"Diet Types: {diet_types}")
        
        meal_types = db.execute(text("SELECT DISTINCT meal_type FROM food_items")).fetchall()
        print(f"Meal Types: {meal_types}")
        
        # Sample row
        sample = db.execute(text("SELECT * FROM food_items LIMIT 1")).fetchone()
        print(f"Sample: {sample}")

    finally:
        db.close()

if __name__ == "__main__":
    inspect_values()
