from fastapi.testclient import TestClient
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.main import app
from app.database import SessionLocal
from app.models.user import User
from app.models.user_profile import UserProfile

client = TestClient(app)

def test_generate_meal_plan_flow():
    # 1. Create a dummy user and profile in the DB directly
    db = SessionLocal()
    
    # Check if user exists or create
    user = db.query(User).filter(User.email == "test@example.com").first()
    if not user:
        user = User(name="testuser", email="test@example.com", password="fakehash", age=25, gender="male")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Check if profile exists
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(
            user_id=user.id,
            weight=75.0,
            height=175.0,
            weight_goal=70.0,
            fitness_goal="weight_loss",
            activity_level="moderate",
            diet_type="non_veg",
            country="India"
        )
        db.add(profile)
        db.commit()
    
    user_id = user.id
    db.close()

    # Debug: Print all routes
    print("Available Routes:")
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"- {route.path}")

    # 2. Call the Generate Endpoint
    # Note: Ensure OPENROUTER_API_KEY is set in the environment where this runs
    response = client.post(f"/meal-plans/generate?user_id={user_id}")
    
    # 3. Verify Response
    if response.status_code == 200:
        data = response.json()
        print("Generation Success!")
        print(f"Plan for User ID: {data['user_profile_id']}")
        for meal in data['meal_plan']:
            print(f"- {meal['label']}: {meal['dish_name']} (P:{meal['nutrients']['p']}, C:{meal['nutrients']['c']}, F:{meal['nutrients']['f']})")
    else:
        print(f"Failed: {response.status_code}")
        print(response.json())

if __name__ == "__main__":
    test_generate_meal_plan_flow()
