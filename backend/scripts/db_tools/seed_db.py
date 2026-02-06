import sys
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))

# Add the backend directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal, engine, Base
from app.models.food_item import FoodItem

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def seed_food_items():
    db = SessionLocal()
    
    # Check if we already have items
    if db.query(FoodItem).count() > 0:
        print("Food items already seeded.")
        return

    items = [
        # Weight Loss Items
        FoodItem(name="Oats Porridge", category="breakfast", calories=150, protein=5, carbs=27, fat=3, is_veg=True, fitness_goal="weight_loss", serving_size="1 bowl"),
        FoodItem(name="Egg Whites Omelette", category="breakfast", calories=70, protein=15, carbs=1, fat=0, is_veg=False, fitness_goal="weight_loss", serving_size="3 eggs"),
        FoodItem(name="Grilled Chicken Salad", category="lunch", calories=300, protein=30, carbs=10, fat=10, is_veg=False, fitness_goal="weight_loss", serving_size="1 plate"),
        FoodItem(name="Quinoa & Veggies", category="dinner", calories=250, protein=8, carbs=40, fat=5, is_veg=True, fitness_goal="weight_loss", serving_size="1 cup"),
        FoodItem(name="Green Tea", category="snack", calories=0, protein=0, carbs=0, fat=0, is_veg=True, fitness_goal="weight_loss", serving_size="1 cup"),
        
        # Muscle Gain Items
        FoodItem(name="Peanut Butter Banana Toast", category="breakfast", calories=400, protein=12, carbs=50, fat=18, is_veg=True, fitness_goal="muscle_gain", serving_size="2 slices"),
        FoodItem(name="Chicken Beast & Rice", category="lunch", calories=600, protein=50, carbs=70, fat=10, is_veg=False, fitness_goal="muscle_gain", serving_size="200g chicken + 1 cup rice"),
        FoodItem(name="Salmon & Sweet Potato", category="dinner", calories=550, protein=40, carbs=45, fat=20, is_veg=False, fitness_goal="muscle_gain", serving_size="1 fillet + 1 potato"),
        FoodItem(name="Greek Yogurt & Nuts", category="snack", calories=200, protein=15, carbs=10, fat=12, is_veg=True, fitness_goal="muscle_gain", serving_size="1 cup"),
        
        # General/Maintenance (All)
        FoodItem(name="Dal Tadka & Rice", category="lunch", calories=450, protein=15, carbs=60, fat=12, is_veg=True, fitness_goal="all", serving_size="1 bowl"),
        FoodItem(name="Mixed Fruit Bowl", category="snack", calories=100, protein=1, carbs=25, fat=0, is_veg=True, fitness_goal="all", serving_size="1 bowl"),
    ]
    
    for item in items:
        db.add(item)
    
    db.commit()
    print("Seeded food items successfully.")
    db.close()

if __name__ == "__main__":
    seed_food_items()
