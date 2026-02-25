from fastapi.testclient import TestClient
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
import sys
import sys, os; from pathlib import Path; sys.path.insert(0, str([p for p in Path(__file__).resolve().parents if (p / 'backend').exists()][0] / 'backend')) # modified

from app.main import app

client = TestClient(app)

def test_user_6():
    print("Testing generation for User ID 6...")
    response = client.post(f"/meal-plans/generate?user_id=6")
    
    if response.status_code == 200:
        data = response.json()
        print("Success!")
        print(f"Plan for User Profile: {data['user_profile_id']}")
        print(f"Items generated: {len(data['meal_plan'])}")
    else:
        print(f"Failed: {response.status_code}")
        print(response.json())

if __name__ == "__main__":
    test_user_6()
