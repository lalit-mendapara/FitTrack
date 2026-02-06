from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.tracking import FoodLog
from app.models.user import User
from app.database import SQLALCHEMY_DATABASE_URL
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Setup DB
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def debug_data():
    try:
        # 1. List Users
        print("--- Users ---")
        users = db.query(User).all()
        for u in users:
            print(f"User: {u.id}, {u.email}")
            
        # Find lalit
        user = db.query(User).filter(User.email == "lalit@gmail.com").first()
        if not user:
            print("User lalit not found")
            return
            
        user_id = user.id
        print(f"\n--- Logs for User {user_id} ({user.email}) ---")
        
        # 2. List recent logs
        logs = db.query(FoodLog).filter(FoodLog.user_id == user_id).order_by(FoodLog.date.desc()).limit(20).all()
        for log in logs:
            print(f"Date: {log.date}, Meal: {log.food_name}, Cals: {log.calories}, Type: {log.meal_type}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_data()
