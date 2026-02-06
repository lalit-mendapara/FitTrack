from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.tracking import FoodLog
from app.models.user import User
from app.database import SQLALCHEMY_DATABASE_URL
from datetime import date, timedelta
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def create_log():
    try:
        user = db.query(User).filter(User.email == "lalit@gmail.com").first()
        if not user:
            print("User not found")
            return

        today = date.today()
        yesterday = today - timedelta(days=1)
        
        print(f"Adding log for {yesterday}...")
        
        log = FoodLog(
            user_id=user.id,
            date=yesterday,
            food_name="Test Meal Yesterday",
            meal_type="Lunch",
            calories=500,
            protein=20,
            carbs=50,
            fat=10
        )
        
        db.add(log)
        db.commit()
        print(f"Log added with ID: {log.id}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_log()
