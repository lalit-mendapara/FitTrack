import sys
import os
import unittest
import json
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.ext.compiler import compiles

# Add backend path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Fix JSONB for SQLite
@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

from app.database import Base
from app.models.food_item import FoodItem
from app.models.user_profile import UserProfile
from app.models.meal_plan import MealPlan
from app.crud.meal_plan import generate_meal_plan_for_user

# Use an in-memory SQLite DB for testing logic only
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class TestCorrectionPipeline(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        
        # 1. Create a User Profile
        self.profile = UserProfile(
            user_id=999,
            fitness_goal="maintenance",
            diet_type="veg",
            country="India",
            calories=2000,
            protein=100,
            carbs=250,
            fat=60
        )
        self.db.add(self.profile)
        
        # 2. Create a Food Item with KNOWN macros
        # "Test Rice": 100g = 130 kcal, 2.7g P, 28g C, 0.3g F
        self.food_item = FoodItem(
            fdc_id="9999",
            name="Test Rice",
            diet_type="veg",
            meal_type="lunch",
            serving_size_g=100.0,
            protein_g=2.7,
            fat_g=0.3,
            carb_g=28.0,
            calories_kcal=130.0,
            region="India"
        )
        self.db.add(self.food_item)
        self.db.commit()
        
    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    @patch('app.crud.meal_plan.httpx.Client')
    def test_auto_correction_activates(self, mock_client_cls):
        # Mock LLM Response with INCORRECT macros for "Test Rice"
        # LLM says: 100g Rice has 500 Calories and 100g Protein (Blatantly wrong)
        
        meal_plan_data = {
            "meal_plan": [
                 {
                  "meal_id": "lunch",
                  "label": "Lunch",
                  "is_veg": True,
                  "dish_name": "Test Rice", # Matches DB name
                  "portion_size": "100g",   # standard portion
                  "nutrients": { "calories": 500, "p": 100, "c": 100, "f": 100 }, # WRONG
                  "alternatives": ["Alt 1"],
                  "guidelines": ["Eat well"]
                }
            ]
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Mocking both text and json() since the code might use either
        mock_response.text = json.dumps(meal_plan_data) 
        mock_response.json.return_value = {
            "message": {
                "role": "assistant",
                "content": json.dumps(meal_plan_data)
            }
        }
        
        # Setup mock behavior
        mock_instance = mock_client_cls.return_value
        mock_instance.__enter__.return_value.post.return_value = mock_response
        mock_instance.__enter__.return_value.get.return_value.status_code = 200 # for heartbeat check
        
        # Run generation
        print("\n--- Running Generation with Mocked LLM (Wrong Macros) ---")
        result = generate_meal_plan_for_user(self.db, 999)
        
        # Assertions
        self.assertIsNotNone(result)
        
        # Check the saved meal in DB
        saved_meal = self.db.query(MealPlan).filter(MealPlan.dish_name == "Test Rice").first()
        self.assertIsNotNone(saved_meal)
        
        print(f"Saved Macros: {saved_meal.nutrients}")
        
        # It should match the DB values (2.7, 28, 0.3), NOT the LLM values (100, 100, 100)
        self.assertEqual(float(saved_meal.nutrients['p']), 2.7)
        self.assertEqual(float(saved_meal.nutrients['c']), 28.0)
        self.assertEqual(float(saved_meal.nutrients['f']), 0.3)
        
        # Check Result Objects
        self.assertEqual(result.meal_plan[0].nutrients.p, 2.7)
        
        print("\n✅ Verification Passed: Auto-correction successfully overwrote incorrect LLM values.")

if __name__ == '__main__':
    unittest.main()
