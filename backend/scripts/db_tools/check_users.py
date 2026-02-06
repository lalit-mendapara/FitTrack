import sys
import os
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.database import SessionLocal
from app.models.user import User
from app.models.user_profile import UserProfile

def check_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Total Users: {len(users)}")
        for u in users:
            profile = db.query(UserProfile).filter(UserProfile.user_id == u.id).first()
            print(f"User ID: {u.id}, Name: {u.name}, Email: {u.email}, Has Profile: {profile is not None}")
            if profile:
                print(f"  - Profile ID: {profile.id}, Goal: {profile.fitness_goal}, Diet: {profile.diet_type}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()
