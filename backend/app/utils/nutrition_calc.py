import re
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.food_item import FoodItem

def parse_portion_grams(portion_string: str) -> float:
    """
    Extracts the gram value from a portion string.
    Examples:
        "100g" -> 100.0
        "2 pcs (50g)" -> 50.0
        "approx 150 grams" -> 150.0
        "1 cup" -> None (unless we add unit conversion later)
    """
    if not portion_string:
        return None
        
    # Normalize
    s = portion_string.lower().strip()
    
    # 1. Look for explicit grams pattern like "100g" or "100 g" or "100grams"
    # This regex looks for a number followed optionally by space, then 'g' or 'gm' or 'gram'
    # We prioritize the LAST occurrence if multiple (e.g. "2 pcs (100g)") usually implies the total weight
    # But actually "200g (2 pcs)" -> 200. Let's look for all matches.
    
    matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:g|gm|grams|gram)\b', s)
    if matches:
        # Usually checking the one inside parens is safer if both exist, but typically there's one weight.
        # Let's verify if there is a specific pattern like "x g"
        try:
           return float(matches[0]) 
        except:
            pass
            
    # If no explicit grams, we can't safely guess mass from "pcs" or "cups" without a density DB.
    # Return None to signal "Cannot determine mass".
    return None

def calculate_macros_from_db(dish_name: str, portion_string: str, db: Session):
    """
    Attempts to find the dish in the DB and calculate strictly based on portion size.
    Returns: { "p": val, "c": val, "f": val, "calories": val } or None
    """
    portion_g = parse_portion_grams(portion_string)
    if not portion_g:
        return None
        
    if not dish_name:
        return None
        
    # Clean dish name for search (remove [CUSTOM], special chars)
    search_name = dish_name.replace("[CUSTOM]", "").replace("(Veg)", "").replace("(Non-Veg)", "").strip()
    search_name = re.sub(r'\s+', ' ', search_name) # normalize spaces
    
    # Stratified Search Strategy
    
    # 1. Exact Match (Case insensitive)
    item = db.query(FoodItem).filter(func.lower(FoodItem.name) == search_name.lower()).first()
    
    # 2. Startswith Match
    if not item:
        item = db.query(FoodItem).filter(func.lower(FoodItem.name).like(f"{search_name.lower()}%")).first()
        
    # 3. Contains Match (Broad) - Pick the shortest name match to avoid "Chicken Salad" matching "Chicken Salad Sandwich" maybe?
    # Actually, simpler is better for now.
    if not item:
         item = db.query(FoodItem).filter(FoodItem.name.ilike(f"%{search_name}%")).first()
         
    if not item:
        return None
        
    # Calculate
    ratio = portion_g / 100.0
    
    return {
        "p": float(item.protein_g) * ratio,
        "c": float(item.carb_g) * ratio,
        "f": float(item.fat_g) * ratio,
        "calories": float(item.calories_kcal) * ratio,
        "source": f"DB: {item.name}"
    }

def enforce_consistency(nutrients: dict) -> dict:
    """
    Ensures Calories = 4P + 4C + 9F.
    Updates 'calories' if the difference is significant.
    """
    p = float(nutrients.get('p', 0))
    c = float(nutrients.get('c', 0))
    f = float(nutrients.get('f', 0))
    cal = float(nutrients.get('calories', 0))
    
    calculated_cal = (p * 4) + (c * 4) + (f * 9)
    
    # If diff > 10% or > 20 kcal, overwrite
    if abs(cal - calculated_cal) > 20:
        nutrients['calories'] = round(calculated_cal)
        nutrients['note'] = "Auto-corrected calories based on macros"
        
    return nutrients

def calculate_bmr(weight: float, height: float, age: int, gender: str) -> float:
    """
    Mifflin-St Jeor Equation to calculate BMR.
    """
    s = 5 if gender.lower() == 'male' else -161
    return (10 * weight) + (6.25 * height) - (5 * age) + s

def calculate_target_workout_burn(bmr: float, activity_level: str, days_per_week: int) -> float:
    """
    Calculates the target calories to burn PER WORKOUT SESSION.
    Assumes that the 'activity_level' chosen by the user is fulfilled primarily by this workout regimen.
    
    Formula:
    Daily_Exercise_Deficit = TDEE(Selected) - TDEE(Sedentary)
    Weekly_Burn_Needed = Daily_Exercise_Deficit * 7
    Session_Burn = Weekly_Burn_Needed / Days_Per_Week
    """
    if days_per_week <= 0:
        return 0.0
        
    activity_multiplier = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'extra_active': 1.9
    }.get(activity_level.lower(), 1.2)
    
    # Baseline Sedentary TDEE = BMR * 1.2
    # This represents non-exercise living.
    baseline_burn = bmr * 1.2
    target_daily_burn = bmr * activity_multiplier
    
    # The burn contributed by "Exercise" (and extra activity)
    daily_exercise_burn = target_daily_burn - baseline_burn
    
    # If user selected Sedentary (1.2), difference is 0.
    # But if they are requesting a workout plan, we must provide *some* burn.
    # We assign a logical minimum for a "Work out" (e.g., 150 kcal - very light / 20 mins).
    if daily_exercise_burn < 50:
        target_session_burn = 150.0
    else:
        # Total weekly burn needed to sustain that activity level
        weekly_exercise_burn = daily_exercise_burn * 7
        target_session_burn = weekly_exercise_burn / days_per_week
        
    return round(target_session_burn)

def calculate_active_exercise_burn(
    user_weight_kg: float, 
    category: str, 
    difficulty: str, 
    is_cardio: bool, 
    sets: int = 3, 
    reps: int = 10,
    duration_str: str = None,
    exercise_name: str = "" # New parameter for better heuristic
) -> float:
    """
    Calculates the calories burned for a specific exercise based on MET values.
    Uses exercise_name to infer intensity if category is generic.
    """
    
    # 1. Determine MET Value (Metabolic Equivalent)
    met = 3.5 # Default: Light Calisthenics
    
    cat_lower = (category or "").lower()
    name_lower = (exercise_name or "").lower()
    
    # Combined text for keyword search
    full_text = f"{name_lower} {cat_lower}"
    
    if is_cardio:
        # Cardio METs
        if "sprint" in full_text: met = 12.0
        elif "hiit" in full_text or "interval" in full_text: met = 11.0
        elif "run" in full_text or "jog" in full_text: met = 9.8
        elif "swim" in full_text: met = 8.0
        elif "row" in full_text: met = 7.0
        elif "cycle" in full_text or "bike" in full_text or "spin" in full_text: met = 7.5
        elif "walk" in full_text: met = 3.8
        elif "elliptical" in full_text: met = 5.0
        else: met = 8.0 # General Cardio
    else:
        # Strength METs Heuristics
        
        # Tier 1: Heavy Compounds (Squat, Deadlift, Clean, Press)
        if any(x in full_text for x in ['squat', 'deadlift', 'clean', 'snatch', 'bench press', 'overhead press', 'military press']):
            met = 6.0
        # Tier 2: Large Muscle Groups (Leg Press, Lunges, Rows, Pullups, Dips)
        elif any(x in full_text for x in ['leg press', 'lunge', 'row', 'pull up', 'chin up', 'dip', 'chest press', 'lat pulldown']):
            met = 5.0
        # Tier 3: Isolation / Accessory (Curls, Extensions, Raises, Flys)
        elif any(x in full_text for x in ['curl', 'extension', 'raise', 'fly', 'kickback', 'crunch', 'sit up', 'calf']):
            met = 3.5
        # Tier 4: Static / Very Isolation (Plank, Wall Sit, Neck)
        elif any(x in full_text for x in ['plank', 'wall sit', 'yoga']):
            met = 2.5
        
        # Fallback to category if name didn't match
        elif any(x in cat_lower for x in ['leg', 'back', 'chest', 'compound', 'olympic']):
            met = 5.5 
        elif any(x in cat_lower for x in ['arm', 'bicep', 'tricep', 'shoulder', 'abs', 'core']):
            met = 3.5
        else:
            met = 4.0 # General Strength (lowered default)

    # Adjust MET for difficulty
    if difficulty:
        if "advanced" in difficulty.lower(): met *= 1.2
        elif "beginner" in difficulty.lower(): met *= 0.9

    # 2. Determine Duration (Minutes)
    duration_min = 0.0
    
    # Priority 1: Explicit Duration String (e.g., "Plank" with "60 sec" or Cardio "20 mins")
    # Check reps field too if it contains time like "60 sec"
    time_source = f"{duration_str} {reps}" 
    
    # Check for "X min"
    min_match = re.search(r'(\d+)\s*min', time_source)
    if min_match:
        duration_min = float(min_match.group(1))
    else:
        # Check for "X sec"
        sec_match = re.search(r'(\d+)\s*sec', time_source)
        if sec_match:
            duration_min = float(sec_match.group(1)) / 60.0

    # Priority 2: Volume Estimation (Sets * Reps * TimePerRep)
    if duration_min == 0:
        # Logic: Heavier weights take longer per rep, but fewer reps. 
        # Lighter weights take less time per rep but more reps.
        # Average "Time Under Tension" heuristic: 
        # Standard rep = 4 seconds (2 down, 2 up)
        
        # If reps is a string range "8-12", take average 10.
        avg_reps = 10
        if isinstance(reps, int):
            avg_reps = reps
        elif isinstance(reps, str):
            digits = re.findall(r'\d+', reps)
            if digits:
                avg_reps = sum(map(int, digits)) / len(digits)
        
        # Active min = Sets * Reps * (4s / 60)
        # Adding buffer for setup between sets? No, MET usually applies to the active bout.
        # Resting burns significantly less. We focus on active burn.
        duration_min = sets * avg_reps * (4.5 / 60.0)
        
    # 3. Calculate Burn
    calories = (met * 3.5 * user_weight_kg / 200) * duration_min
    
    return round(calories)


