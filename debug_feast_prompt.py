import sys
import os
import logging
from unittest.mock import MagicMock
from datetime import date

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)

from app.services.feast_mode_manager import FeastModeManager
from app.models.feast_config import FeastConfig
from app.models.meal_plan import MealPlan

def test_prompt_generation():
    print("\n=== STARTING PROMPT GENERATION TEST ===\n")
    
    # Mock DB
    mock_db = MagicMock()
    
    # Mock Manager
    manager = FeastModeManager(mock_db)
    
    # Mock Data
    config = FeastConfig(
        user_id=1,
        event_name="Wedding",
        event_date=date(2025, 12, 25),
        daily_deduction=300,
        target_bank_calories=3000,
        selected_meals=["lunch", "dinner"]
    )
    
    # Mock Remaining Items
    meal1 = MealPlan(
        meal_id="Lunch",
        dish_name="Chicken Salad",
        portion_size="1 bowl",
        nutrients={"p": 30, "c": 10, "f": 10, "calories": 250}
    )
    meal2 = MealPlan(
        meal_id="Dinner",
        dish_name="Steak and Eggs",
        portion_size="1 steak",
        nutrients={"p": 50, "c": 0, "f": 20, "calories": 380}
    )
    meal3 = MealPlan(
        meal_id="Snack",
        dish_name="Apple",
        portion_size="1 apple",
        nutrients={"p": 0, "c": 20, "f": 0, "calories": 80}
    )
    
    remaining_items = [meal1, meal2, meal3]
    budget = 300 # Debt to remove
    target_date = date(2025, 12, 20) # Banking phase
    selected_ids = ["lunch", "dinner"]
    
    # Mock LLM Service to just print the prompt it receives
    import app.services.llm_service as llm_service
    
    original_call_llm_json = llm_service.call_llm_json
    
    def mock_call_llm_json(system_prompt, user_prompt, temperature=0.1):
        print("\n[MOCK LLM] INTERCEPTED PROMPT:")
        print("-" * 50)
        print(f"SYSTEM PROMPT:\n{system_prompt}")
        print("-" * 50)
        print(f"USER PROMPT:\n{user_prompt}")
        print("-" * 50)
        return {"adjusted_meals": []} # Return dummy
        
    llm_service.call_llm_json = mock_call_llm_json
    
    try:
        manager._generate_overrides_via_llm(config, remaining_items, budget, target_date, selected_ids)
    except Exception as e:
        print(f"Error during execution: {e}")
    finally:
        # Restore (not strictly needed for script but good practice)
        llm_service.call_llm_json = original_call_llm_json

if __name__ == "__main__":
    test_prompt_generation()
