
import logging

logger = logging.getLogger(__name__)

"""
Nutrition Service
-----------------
Handles all the mathematical logic for nutrition planning.
This module is pure business logic and does not depend on the Database or Models directly.
"""

def calculate_daily_targets(
    weight: float,
    height: float,
    age: int,
    gender: str,
    activity_level: str,
    fitness_goal: str,
    diet_type: str,
    weight_goal: float = None
) -> dict:
    """
    Calculates daily calorie and macronutrient targets based on physical attributes.
    
    Algorithm:
    1. BMR (Mifflin-St Jeor)
    2. TDEE (Activity Multiplier)
    3. Goal Adjustment (Deficit/Surplus)
    4. Macro Split (Protein first, then Fat/Carbs based on goal)
    
    Returns:
        dict: { "calories": int, "protein": float, "fat": float, "carbs": float }
    """
    
    if not weight or not height:
        return {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}

    # Normalize inputs
    gender = gender.lower()
    activity_level = (activity_level or 'sedentary').lower()
    fitness_goal = (fitness_goal or 'maintenance').lower()
    diet_type = (diet_type or 'non_veg').lower()
    
    logger.info(f"[Nutrition Service] Calculating for: {weight}kg, {height}cm, {age}yrs, {gender}, {fitness_goal}")

    # 1. Calculate Basal Metabolic Rate (BMR) using Mifflin-St Jeor Equation
    if gender == 'male':
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    
    # 2. Apply Activity Factor
    activity_map = {
        'sedentary': 1.2,        # Little or no exercise
        'light': 1.375,          # Light exercise 1-3 days/week
        'moderate': 1.55,        # Moderate exercise 3-5 days/week
        'active': 1.725,         # Hard exercise 6-7 days/week
        'extra_active': 1.9      # Very hard exercise & physical job
    }
    
    activity_multiplier = activity_map.get(activity_level, 1.2)
    maintenance_calories = bmr * activity_multiplier
    
    # 3. Adjust Calories based on Fitness Goal
    
    # Consistency Check: 
    # If user wants to LOSE weight but selected "Muscle Gain", force logic to "Fat Loss"
    # This ensures they don't gain fat when they need to lose weight.
    if weight_goal and weight > weight_goal:
        if fitness_goal == 'muscle_gain':
            logger.warning("Goal Mismatch: Current > Goal but 'Muscle Gain' selected. Forcing 'fat_loss' logic.")
            fitness_goal = 'fat_loss'

    target_calories = maintenance_calories
    
    if fitness_goal == "weight_loss":
        # Aggressive weight loss: 750-1000 calorie deficit
        target_calories = max(maintenance_calories - 750, bmr * 1.1)
        
    elif fitness_goal == "fat_loss":
        # Moderate fat loss: 500 calorie deficit
        target_calories = max(maintenance_calories - 500, bmr * 1.1)
        
    elif fitness_goal == "muscle_gain":
        # Lean muscle gain: 300 calorie surplus
        target_calories = maintenance_calories + 300
        
    # 4. Calculate Protein
    if fitness_goal in ["weight_loss", "fat_loss"]:
        # Moderate high protein: 1.6 - 1.8 g/kg (REALISTIC)
        protein_per_kg = 1.8 if activity_level in ['active', 'extra_active'] else 1.6
    elif fitness_goal == "muscle_gain":
        # Moderate high protein: 1.6 - 1.8 g/kg (REALISTIC)
        protein_per_kg = 1.8 if activity_level in ['active', 'extra_active'] else 1.6
    else:
        # Maintenance: 1.2 - 1.4 g/kg
        protein_per_kg = 1.4 if activity_level in ['active', 'extra_active'] else 1.2

    # Vegetarian Adjustment (lower bioavailability -> slightly higher need)
    if diet_type == "veg":
        protein_per_kg = min(protein_per_kg * 1.1, 2.0) # Cap at 2.0g/kg

    protein = round(weight * protein_per_kg, 1)
    protein_calories = protein * 4

    # 5. Calculate Fat (25-35% of total calories)
    if fitness_goal in ["weight_loss", "fat_loss"]:
        fat_percentage = 0.30 # Increased from 0.25
    elif fitness_goal == "muscle_gain":
        fat_percentage = 0.35 # Increased from 0.30
    else:
        fat_percentage = 0.35 # Increased from 0.30
    
    fat = round((target_calories * fat_percentage) / 9, 1)
    fat_calories = fat * 9

    # 6. Calculate Carbs (Remainder)
    remaining_calories = target_calories - protein_calories - fat_calories
    carbs = max(round(remaining_calories / 4, 1), 0)

    # 7. Minimum Safety Checks
    # Minimum Carbs for brain function (~130g)
    if carbs < 130:
        # Reduce fat to allow for carbs
        min_fat_grams = weight * 0.5 # Absolute minimum fat 0.5g/kg
        current_fat = fat
        
        # Try to lower fat to minimum 20%
        target_fat_cals = target_calories * 0.20
        target_fat = target_fat_cals / 9
        
        if target_fat < current_fat:
            fat = max(target_fat, min_fat_grams)
            fat_calories = fat * 9
            remaining_calories = target_calories - protein_calories - fat_calories
            carbs = max(round(remaining_calories / 4, 1), 0)
            
        # If still low, just force 130g and increase calories (Safety over deficit)
        if carbs < 130:
            carbs = 130

    # 8. Final Rounding
    return {
        "calories": round(target_calories),
        "protein": round(protein, 1),
        "fat": round(fat, 1),
        "carbs": round(carbs, 1)
    }

