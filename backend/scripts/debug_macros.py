import sys
import os
import re

# Add backend directory to sys.path
sys.path.append(os.getcwd())

from sqlalchemy import func
from app.database import SessionLocal
from app.models.user_profile import UserProfile
from app.models.meal_plan import MealPlan
from app.models.food_item import FoodItem

def parse_portion_string(portion_str):
    """
    Parses strings like "1.5 servings of Paneer Tikka Masala, 1 serving of Jeera Rice"
    Returns list of (multiplier, food_name_fragment)
    """
    # Split by comma or ' + '
    parts = re.split(r',|\+', portion_str)
    parsed_items = []
    
    for part in parts:
        part = part.strip()
        if not part: continue
        
        # Regex for "X serving(s) of Y"
        match = re.search(r'([\d\.]+)\s*servings?\s*of\s*(.*)', part, re.IGNORECASE)
        if match:
            multiplier = float(match.group(1))
            name = match.group(2).strip()
            parsed_items.append((multiplier, name))
        else:
            # Fallback: assume 1 serving if just a name, or "1 serving each"
            if "serving each" in part:
                 # Logic for "Food A + Food B ... Portion: 1 serving each"
                 # This is tricky because the portion string usually doesn't list the foods if it just says "1 serving each"
                 # We'll handle this in the main loop by falling back to Dish Name if Portion is generic
                 return None 
            
            # Assume 1.0
            parsed_items.append((1.0, part))
            
    return parsed_items

def debug_macros():
    db = SessionLocal()
    try:
        user_profile = db.query(UserProfile).order_by(UserProfile.id.desc()).first()
        if not user_profile:
            print("No user profile found.")
            return

        print(f"DEBUGGING MACROS FOR USER ID: {user_profile.id}")
        print(" Using Portion Size for Quantity * DB Food Item Macros")
        print("-" * 60)

        meal_plans = db.query(MealPlan).filter(MealPlan.user_profile_id == user_profile.id).all()
        
        for meal in meal_plans:
            print(f"\nMEAL: {meal.label.upper()}")
            print(f"DISH: {meal.dish_name}")
            print(f"PORTION TEXT: {meal.portion_size}")
            
            # Generated
            gen_p = float(meal.nutrients.get('p', 0))
            gen_c = float(meal.nutrients.get('c', 0))
            gen_f = float(meal.nutrients.get('f', 0))
            gen_cal = (gen_p * 4) + (gen_c * 4) + (gen_f * 9)

            print(f"GENERATED -> P: {gen_p}g | C: {gen_c}g | F: {gen_f}g | KCAL: {gen_cal:.0f}")

            # Calculate Actual
            actual_p = 0; actual_c = 0; actual_f = 0; actual_cal = 0
            
            # Strategy:
            # 1. Try to parse specific portion quantities from 'portion_size'
            # 2. If 'portion_size' is generic (e.g. "1 serving each"), parse 'dish_name' and assume 1.0
            
            items_to_process = []
            
            parsed_portions = parse_portion_string(meal.portion_size)
            
            is_generic_portion = "serving each" in meal.portion_size.lower() or not parsed_portions
            
            if is_generic_portion:
                # Use Dish Name split
                names = [n.strip() for n in meal.dish_name.split('+')]
                # Filter out "extra serving of..." text from dish name if we are doing simple split
                # actually, "extra serving of X" acts like X.
                clean_names = []
                for n in names:
                    if "extra serving of" in n:
                        clean_names.append(n.replace("extra serving of", "").strip())
                    else:
                        clean_names.append(n)
                
                items_to_process = [(1.0, n) for n in clean_names]
            else:
                items_to_process = parsed_portions

            print(f"ANALYSIS:")
            for qty, name in items_to_process:
                # Lookup
                food_item = db.query(FoodItem).filter(func.lower(FoodItem.name) == name.lower()).first()
                if not food_item:
                    food_item = db.query(FoodItem).filter(FoodItem.name.ilike(f"%{name}%")).first()
                
                if food_item:
                    p = float(food_item.protein_g or 0) * qty
                    c = float(food_item.carb_g or 0) * qty
                    f = float(food_item.fat_g or 0) * qty
                    cal = float(food_item.calories_kcal or 0) * qty
                    
                    actual_p += p
                    actual_c += c
                    actual_f += f
                    actual_cal += cal
                    
                    print(f"  [FOUND] {qty}x {food_item.name}: {cal:.0f}kcal (P:{p:.1f}/C:{c:.1f}/F:{f:.1f})")
                else:
                    print(f"  [MISSING] Could not find '{name}' in DB")

            print(f"TOTAL ACTUAL -> P: {actual_p:.1f}g | C: {actual_c:.1f}g | F: {actual_f:.1f}g | KCAL: {actual_cal:.0f}")
            
            diff_cal = gen_cal - actual_cal
            print(f"DIFF (Gen - Act) -> KCAL: {diff_cal:+.0f}")
            print("-" * 60)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_macros()
