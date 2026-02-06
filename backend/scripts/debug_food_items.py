import sys
import os
from sqlalchemy import func

# Add backend to path
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.food_item import FoodItem

def check_food_items():
    db = SessionLocal()
    items = db.query(FoodItem).all()
    print(f"Total items: {len(items)}")
    
    # Check for some lighter options
    light_items = db.query(FoodItem).filter(FoodItem.fat_g < 5, FoodItem.calories_kcal < 150).limit(5).all()
    print("\nSample Light Items:")
    for i in light_items:
        print(f"- {i.name} (Cal: {i.calories_kcal}, Fat: {i.fat_g})")
        
    db.close()

if __name__ == "__main__":
    check_food_items()
