
import json
import logging
import re
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, not_
from sqlalchemy.orm.attributes import flag_modified

from app.models.user_profile import UserProfile
from app.models.food_item import FoodItem
from app.models.meal_plan import MealPlan
from app.models.meal_plan_history import MealPlanHistory
from app.schemas.meal_plan import MealPlanResponse, MealItem, NutrientDetail, NutrientTotals
from app.crud.meal_plan import update_single_meal

from app.services.vector_service import VectorService

from app.services import llm_service
from app.services import nutrition_service
from app.services import ingredient_mapper
from app.crud import meal_plan as crud_meal_plan

logger = logging.getLogger(__name__)

"""
Meal Plan Service
-----------------
Orchestrates the generation of Meal Plans.
1. Validates user request.
2. Refreshes nutrition targets.
3. Fetches relevant food items (Business Logic).
4. Calls LLM to compose the plan.
5. Validates macro deviation (±5%).
6. Saves the plan to DB.
"""

def get_meal_ratios_by_fitness_goal(fitness_goal: str) -> dict:
    """
    Returns calorie distribution ratios per meal based on fitness goal.
    
    Ratios:
    - Muscle Gain: Breakfast 25%, Lunch 30%, Dinner 30%, Snacks 15%
    - Fat Loss:    Breakfast 30%, Lunch 30%, Dinner 25%, Snacks 15%
    - Weight Loss: Breakfast 25%, Lunch 35%, Dinner 25%, Snacks 15%
    - Maintenance: Breakfast 25%, Lunch 30%, Dinner 25%, Snacks 20%
    """
    fitness_goal = (fitness_goal or 'maintenance').lower()
    
    ratios_map = {
        "muscle_gain": {"breakfast": 0.25, "lunch": 0.30, "dinner": 0.30, "snacks": 0.15},
        "fat_loss":    {"breakfast": 0.30, "lunch": 0.30, "dinner": 0.25, "snacks": 0.15},
        "weight_loss": {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.25, "snacks": 0.15},
        "maintenance": {"breakfast": 0.25, "lunch": 0.30, "dinner": 0.25, "snacks": 0.20}
    }
    
    return ratios_map.get(fitness_goal, ratios_map["maintenance"])


def get_region_from_country(country_name: str) -> str:
    """Map country names to broader culinary regions."""
    if not country_name:
        return "India"
    
    country_lower = country_name.lower().strip()
    
    # Special case: India maps directly to "India" region
    if "india" in country_lower:
        return "India"
    
    # Asia region (excluding India)
    asia_countries = [
        "china", "japan", "thailand", "vietnam", "korea", "south korea", "north korea",
        "pakistan", "bangladesh", "sri lanka", "nepal", "myanmar", "burma",
        "cambodia", "laos", "philippines", "indonesia", "malaysia", "singapore",
        "taiwan", "hong kong", "mongolia"
    ]
    
    # Europe and Western countries
    europe_countries = [
        "uk", "united kingdom", "england", "scotland", "wales", "ireland",
        "germany", "france", "italy", "spain", "portugal", "greece", "netherlands",
        "belgium", "switzerland", "austria", "poland", "czech", "hungary",
        "romania", "sweden", "norway", "denmark", "finland", "iceland",
        "russia", "ukraine", "turkey"
    ]
    
    # North America
    north_america_countries = [
        "usa", "united states", "america", "canada", "mexico"
    ]
    
    # South America
    south_america_countries = [
        "brazil", "argentina", "chile", "colombia", "peru", "venezuela",
        "ecuador", "bolivia", "paraguay", "uruguay", "guyana", "suriname"
    ]
    
    # Africa
    africa_countries = [
        "nigeria", "kenya", "egypt", "south africa", "ethiopia", "tanzania",
        "ghana", "uganda", "morocco", "algeria", "tunisia", "sudan",
        "angola", "mozambique", "cameroon", "ivory coast", "madagascar",
        "senegal", "zimbabwe", "libya"
    ]
    
    # Australia/Oceania
    oceania_countries = [
        "australia", "new zealand", "fiji", "papua new guinea", "samoa",
        "tonga", "vanuatu", "solomon islands"
    ]
    
    # Check each region
    if any(c in country_lower for c in asia_countries):
        return "Asia"
    if any(c in country_lower for c in europe_countries):
        return "Europe"
    if any(c in country_lower for c in north_america_countries):
        return "North America"
    if any(c in country_lower for c in south_america_countries):
        return "South America"
    if any(c in country_lower for c in africa_countries):
        return "Africa"
    if any(c in country_lower for c in oceania_countries):
        return "Australia/Oceania"
    
    # Default fallback
    return "India"


def get_food_items_filtered(
    db: Session, 
    diet_type: str = None, 
    region: str = None, 
    country: str = None,
    meal_type: str = None,
    limit: int = 50
) -> List[FoodItem]:
    """
    Fetches food items with filtering strategy:
    1. Filter by diet_type first (veg users get only veg)
    2. Filter by region/country (prioritized)
    3. Optionally filter by meal_type
    4. Apply limit to optimize token usage
    Returns a focused dataset for LLM consumption.
    """
    query = db.query(FoodItem)
    
    # 1. Diet Type Filter
    # "both" -> No filter (fetch all)
    # "veg" -> Strict veg filter
    # "non_veg" -> Strict non-veg filter
    if diet_type:
        dt = diet_type.lower()
        if dt in ["veg", "vegetarian"]:
            query = query.filter(FoodItem.diet_type == "veg")
        elif dt in ["non_veg", "non-veg", "nonveg"]:
            # Smart Filter: Allow Non-Veg OR (Veg AND NOT Main_Course_Keywords)
            # This allows sides (Rice, Roti, Salad) but blocks Paneer/Dal/etc.
            exclusions = ['paneer', 'dal', 'tofu', 'soya', 'rajma', 'chole', 'kofta', 'mushroom', 'curry', 'bhurji']
            
            # Build negation clauses: name NOT ILIKE '%keyword%'
            negation_clauses = [~FoodItem.name.ilike(f"%{kw}%") for kw in exclusions]
            
            query = query.filter(
                or_(
                    FoodItem.diet_type == 'non-veg',
                    and_(
                        FoodItem.diet_type == 'veg',
                        *negation_clauses
                    )
                )
            )
    
    # 2. Region/Country Filter with tiered fallback strategy
    items = []
    
    # Tier 1: Try exact country match first (e.g., "India")
    if country:
        country_query = query.filter(func.lower(FoodItem.region) == country.lower())
        if meal_type:
            country_query = country_query.filter(FoodItem.meal_type.ilike(f"%{meal_type}%"))
        # Limit country-specific items to ensure we get variety
        items = country_query.limit(limit).all()
    
    # Tier 2: If not enough, try broader region match
    # Tier 2: If not enough, try broader region match
    if len(items) < 20 and region and (region.lower() != country.lower() if country else True):
        region_query = query.filter(func.lower(FoodItem.region) == region.lower())
        if meal_type:
            region_query = region_query.filter(FoodItem.meal_type.ilike(f"%{meal_type}%"))
        
        # Get regional items (limited)
        regional_items = region_query.limit(limit - len(items)).all()
        
        # Add unique items
        existing_ids = {i.fdc_id for i in items}
        for item in regional_items:
            if item.fdc_id not in existing_ids:
                items.append(item)
                existing_ids.add(item.fdc_id)
                if len(items) >= limit:
                    break
    
    # Tier 3: Global fallback if still not enough (ensure minimum diversity)
    if len(items) < 15:
        fallback_query = query
        if meal_type:
            fallback_query = fallback_query.filter(FoodItem.meal_type.ilike(f"%{meal_type}%"))
        
        # Get remaining items up to limit
        remaining_needed = min(30, limit - len(items))
        backup = fallback_query.limit(remaining_needed).all()
        
        existing_ids = {i.fdc_id for i in items}
        for item in backup:
            if item.fdc_id not in existing_ids:
                items.append(item)
                if len(items) >= limit:
                    break
    
    logger.info(f"Food filtering: Got {len(items)} items (Region: {region}, Country: {country}, Limit: {limit})")
    return items[:limit]  # Ensure we never exceed limit


def find_food_item_by_name(db: Session, name: str, diet_type: str = None) -> Optional[FoodItem]:
    """
    Search for a specific food item from custom prompt in our database.
    Used to check if a user-requested food exists in our DB.
    
    Returns:
        FoodItem if found, None otherwise
    """
    query = db.query(FoodItem)
    
    # Apply diet filter
    if diet_type:
        dt = diet_type.lower()
        if dt in ["veg", "vegetarian"]:
            query = query.filter(FoodItem.diet_type == "veg")
        elif dt in ["non_veg", "non-veg", "nonveg"]:
            query = query.filter(FoodItem.diet_type == "non-veg")
    
    # 1. Exact match (case-insensitive)
    item = query.filter(func.lower(FoodItem.name) == name.lower().strip()).first()
    if item:
        return item
    
    # 2. Partial match
    item = query.filter(FoodItem.name.ilike(f"%{name.strip()}%")).first()
    return item


def extract_food_names_from_prompt(prompt: str) -> List[str]:
    """
    Extract potential food names from a custom prompt.
    Simple heuristic: look for common patterns like "add X", "I want X", "replace with X"
    """
    if not prompt:
        return []
    
    prompt_lower = prompt.lower()
    food_names = []
    
    # Common patterns
    patterns = [
        r"add\s+(\w+(?:\s+\w+)?)",
        r"i want\s+(\w+(?:\s+\w+)?)",
        r"replace.*with\s+(\w+(?:\s+\w+)?)",
        r"change.*to\s+(\w+(?:\s+\w+)?)",
        r"include\s+(\w+(?:\s+\w+)?)",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, prompt_lower)
        food_names.extend(matches)
    
    return list(set(food_names))


def extract_food_items_from_previous_plan(db: Session, user_profile_id: int) -> List[str]:
    """
    Extract main food items from the user's current meal plan.
    Returns a list of food item names to exclude when regenerating without a custom prompt.
    This ensures variety by avoiding repetition of the same dishes.
    """
    existing_meals = crud_meal_plan.get_meal_plan(db, user_profile_id)
    if not existing_meals:
        return []
    
    excluded_items = []
    # Common sides/accompaniments that we don't need to exclude (they can repeat)
    common_sides = ['salad', 'raita', 'curd', 'cucumber', 'chutney', 'pickle', 'yogurt', 
                    'fruit', 'banana', 'apple', 'tea', 'coffee', 'water', 'roti', 'rice',
                    'chapati', 'naan', 'paratha']
    
    for meal in existing_meals:
        dish_name = meal.dish_name
        portion_size = meal.portion_size
        
        # Extract main items from dish_name (e.g., "Palak Paneer (veg) + Rice + Salad")
        # Split by + and get first part which is usually the main dish
        if dish_name:
            parts = dish_name.split('+')
            for part in parts:
                # Clean up the part
                clean_part = part.strip()
                # Remove (veg) or (non-veg) labels
                clean_part = clean_part.replace('(veg)', '').replace('(non-veg)', '').strip()
                
                # Skip if it's a common side
                if clean_part.lower() in common_sides:
                    continue
                
                # Skip if it's too short (likely not a real dish name)
                if len(clean_part) < 4:
                    continue
                    
                # Skip if it contains only numbers (like "2 Roti")
                if clean_part.replace(' ', '').isdigit():
                    continue
                
                # Check if starts with number (like "2 Roti") and extract the name
                words = clean_part.split()
                if words and words[0].isdigit():
                    clean_part = ' '.join(words[1:])
                
                # Add to exclusion list if it's not a common side
                if clean_part and not any(side in clean_part.lower() for side in common_sides):
                    excluded_items.append(clean_part)
        
        # Also parse portion_size to catch items mentioned there
        if portion_size:
            # Format: "200g Palak Paneer, 150g Rice, 100g Salad"
            items = re.findall(r'\d+(?:\.\d+)?\s*(?:g|ml)\s+([^,]+)', portion_size)
            for item_name in items:
                clean_name = item_name.strip()
                # Skip common sides
                if not any(side in clean_name.lower() for side in common_sides):
                    if len(clean_name) >= 4:
                        excluded_items.append(clean_name)
    
    # Remove duplicates and return
    return list(set(excluded_items))


def validate_macro_deviation(generated: Dict, target: Dict, tolerance: float = 0.05) -> Tuple[bool, Dict]:
    """
    Check if generated macros are within ±5% of target.
    
    Returns:
        Tuple of (is_valid, deviation_details)
    """
    deviations = {}
    is_valid = True
    
    for key in ['calories', 'protein', 'carbs', 'fat']:
        gen_val = float(generated.get(key, 0))
        target_val = float(target.get(key, 0))
        
        if target_val == 0:
            deviations[key] = {"generated": gen_val, "target": target_val, "deviation": 0, "within_tolerance": True}
            continue
            
        deviation = abs(gen_val - target_val) / target_val
        within_tolerance = deviation <= tolerance
        
        deviations[key] = {
            "generated": gen_val,
            "target": target_val,
            "deviation_pct": round(deviation * 100, 1),
            "within_tolerance": within_tolerance
        }
        
        if not within_tolerance:
            is_valid = False
    
    return is_valid, deviations


# Fallback macros for common items not in DB (per 100g)
FALLBACK_MACROS = {
    "curd": {"p": 3.1, "c": 4.0, "f": 4.0, "cal": 60},
    "yogurt": {"p": 3.5, "c": 4.7, "f": 3.3, "cal": 61},
    "apple": {"p": 0.3, "c": 14.0, "f": 0.2, "cal": 52},
    "banana": {"p": 1.1, "c": 23.0, "f": 0.3, "cal": 89},
    "cucumber": {"p": 0.7, "c": 3.6, "f": 0.1, "cal": 15},
    "salad": {"p": 1.0, "c": 5.0, "f": 0.5, "cal": 25},
    "raita": {"p": 2.5, "c": 4.5, "f": 3.5, "cal": 60},
    "chutney": {"p": 1.0, "c": 8.0, "f": 15.0, "cal": 160},
    "tea": {"p": 0.1, "c": 5.0, "f": 1.0, "cal": 30},
    "coffee": {"p": 0.1, "c": 5.0, "f": 1.0, "cal": 30},
    "fruit": {"p": 0.5, "c": 12.0, "f": 0.2, "cal": 50},
    "vegetable": {"p": 1.5, "c": 5.0, "f": 0.2, "cal": 30},
    "roti": {"p": 7.0, "c": 45.0, "f": 2.0, "cal": 230}, # Fallback if specific bread not found
    "roti": {"p": 7.0, "c": 45.0, "f": 2.0, "cal": 230}, # Fallback if specific bread not found
    "rice": {"p": 2.5, "c": 28.0, "f": 0.3, "cal": 130}, # Fallback if specific rice not found
    "chicken": {"p": 27.0, "c": 0.0, "f": 14.0, "cal": 239},
    "fish": {"p": 22.0, "c": 0.0, "f": 12.0, "cal": 206},
    "egg": {"p": 13.0, "c": 1.1, "f": 11.0, "cal": 155},
    "meat": {"p": 26.0, "c": 0.0, "f": 15.0, "cal": 250},
    "paneer": {"p": 18.0, "c": 1.2, "f": 20.0, "cal": 265},
    "dal": {"p": 6.0, "c": 18.0, "f": 1.0, "cal": 105}
}

# Standard weights for unit-based items (fallback if no g/ml provided)
UNIT_WEIGHTS = {
    "apple": 150, "banana": 120, "orange": 130, "pear": 150, "fruit": 150,
    "egg": 50, "slice": 35, "bread": 35, "roti": 40, "chapati": 40, "tortilla": 40,
    "biscuit": 15, "cookie": 20, "piece": 50, "pc": 50, "cup": 240,
    "tbsp": 15, "tsp": 5, "glass": 250, "bowl": 300,
    "curd": 150, "yogurt": 150, "salad": 150  # Default bowl assumption
}

def calculate_meal_macros_from_db(db: Session, portion_str: str) -> Dict:
    """
    Calculate macros for a meal based on portion string using DB values.
    Returns dict with totals and breakdown of items.
    Handles strict units (g/ml) and count-based fallbacks (1 Apple).
    """
    analysis = {
        "items": [], 
        "total_cal": 0, "total_p": 0, "total_c": 0, "total_f": 0
    }
    
    if not portion_str:
        return analysis

    # Split by comma OR plus to handle "Egg + Roti"
    # Replace separators with comma
    clean_str = portion_str.replace('+', ',').replace('&', ',')
    raw_items = [p.strip() for p in clean_str.split(',') if p.strip()]
    
    for part in raw_items:
        weight = 0
        clean_name = ""
        source = "Unknown"
        
        # 1. Try Strict Regex (100g Chicken)
        # Matches: Number + (g|ml) + Name
        strict_match = re.match(r'^(\d+(?:\.\d+)?)\s*(g|ml)\s+(.+)$', part, re.IGNORECASE)
        
        if strict_match:
            qty, unit, name = strict_match.groups()
            weight = float(qty)
            clean_name = name.strip()
            source = "Strict(g/ml)"
            is_fixed = False # Strict weights can be optimized if needed, but usually we treat explicit units as fixed too?
            # Actually, standard bulk items like "100g Rice" are what we optimize.
            # But the optimizer changes the weight number.
            # If the user typed "100g Rice", do they want it fixed?
            # For now, let's treat Strict as Variable ONLY if it ends up being a Source.
        else:
            # 2. Try Count-Based Regex (1 Apple, 2 Slices Bread)
            # Matches: Number + Optional Unit Word + Name
            count_match = re.match(r'^(\d+(?:\.\d+)?)\s*(?:(medium|large|small|piece|pcs|slice|cup|tbsp|tsp|glass|bowl)\b)?\s*(.+)$', part, re.IGNORECASE)
            
            if count_match:
                qty, unit_word, name = count_match.groups()
                count = float(qty)
                clean_name = name.strip()
                name_lower = clean_name.lower()
                
                # Determine weight per unit
                unit_weight = 100 # Default fallback
                found_weight = False
                
                # A. Check explicit unit word (cup, slice)
                if unit_word:
                    uw_lower = unit_word.lower()
                    if uw_lower in UNIT_WEIGHTS:
                        unit_weight = UNIT_WEIGHTS[uw_lower]
                        found_weight = True
                
                # B. Check name against known unit items (Apple, Egg) if not already found
                if not found_weight:
                    for k, w in UNIT_WEIGHTS.items():
                        # exact word match check
                        if re.search(r'\b' + re.escape(k) + r'\b', name_lower):
                            unit_weight = w
                            break
                
                weight = count * unit_weight
                source = f"Count({count}x{unit_weight}g)"
                
                # OPTIMIZATION RELAXATION:
                # Treat scalable count-based items as Variable, not Fixed.
                # This allows the optimizer to reduce "4 Roti" to "2 Roti".
                scalable_items = ["roti", "chapati", "naan", "bread", "slice", "idli", "dosa", "pancake", "waffle"]
                is_scalable = any(s in name_lower for s in scalable_items)
                
                is_fixed = not is_scalable # Variable if scalable, Fixed otherwise
            else:
                # 3. Fallback: No number found? (e.g. "Apple")
                # Assume 1 serving = 100g
                clean_name = part
                weight = 100
                source = "Implicit(100g)"
                is_fixed = True # Implicit items are Fixed

        # Lookup in DB - Strict First
        # 1. Exact Match
        food_item = db.query(FoodItem).filter(func.lower(FoodItem.name) == clean_name.lower()).first()
        
        # 2. Word Boundary Match (Avoid 'apple' matching 'pineapple')
        if not food_item:
             # SQL regex for word boundary typically requires different syntax per DB
             # Easier to fetch potential matches and filter relying on python or stricter ILIKE
             # Postgres: ~* '\yapple\y'
             pass 
        
        if not food_item:
             # Fallback to ilike but prioritized
             food_item = db.query(FoodItem).filter(FoodItem.name.ilike(f"%{clean_name}%")).first()
             # Verify it's not a bad partial match (e.g. Apple vs Pineapple)
             if food_item and clean_name.lower() in food_item.name.lower():
                 # Check if the match is "clean"
                 if "apple" in clean_name.lower() and "pineapple" in food_item.name.lower():
                     # Reject if user asked for apple but got pineapple
                     if "pineapple" not in clean_name.lower():
                         food_item = None
        
        density = None
        if food_item:
            # Use DB macros
            density = {
                "p": float(food_item.protein_g) / 100,
                "c": float(food_item.carb_g) / 100,
                "f": float(food_item.fat_g) / 100,
                "cal": float(food_item.calories_kcal) / 100
            }
            source += f" -> DB({food_item.name})"
        else:
            # Check fallbacks (Use word boundary check)
            name_lower = clean_name.lower()
            
            for key, macs in FALLBACK_MACROS.items():
                if re.search(r'\b' + re.escape(key) + r'\b', name_lower):
                    density = {k: v/100 for k, v in macs.items()}
                    source += f" -> Fallback({key})"
                    break
            
            if not density:
                 for key, macs in FALLBACK_MACROS.items():
                    if len(key) > 3 and key in name_lower:
                        density = {k: v/100 for k, v in macs.items()}
                        source += f" -> Fallback({key})"
                        break
            
            if not density:
                # Default backup
                density = {"p": 0.05, "c": 0.15, "f": 0.05, "cal": 1.25}
                source += " -> Default"
        
        # Calculate contribution
        item_p = weight * density["p"]
        item_c = weight * density["c"]
        item_f = weight * density["f"]
        item_cal = weight * density["cal"]
        
        analysis["items"].append({
            "name": clean_name,
            "weight": weight,
            "density": density,
            "source": source,
            "is_fixed": is_fixed
        })
        
        analysis["total_p"] += item_p
        analysis["total_c"] += item_c
        analysis["total_f"] += item_f
        analysis["total_cal"] += item_cal
        
    return analysis


# ============================================================================
# TWO-PHASE ARCHITECTURE: BACKEND CALCULATION
# ============================================================================

def calculate_portions_from_dishes(
    db: Session, 
    meals: List[Dict], 
    targets: Dict, 
    diet_type: str = None,
    fitness_goal: str = None
) -> List[Dict]:
    """
    PHASE 2 of Two-Phase Architecture: Backend Calculation
    
    Takes LLM-selected dishes and calculates:
    1. Optimal portion sizes (to hit macro targets)
    2. Accurate nutrients (from FoodItem DB)
    
    This is the single source of truth for nutrients - no LLM estimation.
    
    Args:
        db: Database session
        meals: List of meal dicts from LLM (dish_name, is_veg, alternatives, guidelines)
        targets: User's daily macro targets {calories, protein, fat, carbs}
        diet_type: User's diet preference (for ingredient filtering)
        fitness_goal: For meal ratio calculation
    
    Returns:
        List of meals with portion_size and nutrients populated
    """
    print("\n" + "=" * 70)
    print("       PHASE 2: BACKEND CALCULATION (Two-Phase Architecture)")
    print("=" * 70)
    print(f"  Daily Targets: {targets['calories']:.0f}kcal | P:{targets['protein']:.1f}g | C:{targets['carbs']:.1f}g | F:{targets['fat']:.1f}g")
    print("=" * 70)
    
    meal_ratios = get_meal_ratios_by_fitness_goal(fitness_goal)
    total_target_cal = float(targets.get("calories", 2000))
    total_target_p = float(targets.get("protein", 150))
    total_target_c = float(targets.get("carbs", 200))
    total_target_f = float(targets.get("fat", 60))
    
    calculated_meals = []
    
    for meal in meals:
        meal_id = meal.get("meal_id", "meal").lower()
        dish_name = meal.get("dish_name", "")
        
        if meal_id not in meal_ratios:
            meal_ratios[meal_id] = 0.25
        
        # Meal-specific targets
        ratio = meal_ratios[meal_id]
        m_target_cal = total_target_cal * ratio
        m_target_p = total_target_p * ratio
        m_target_c = total_target_c * ratio
        m_target_f = total_target_f * ratio
        
        print(f"\n  📊 {meal_id.upper()} Targets: {m_target_cal:.0f}kcal | P:{m_target_p:.1f}g | C:{m_target_c:.1f}g | F:{m_target_f:.1f}g")
        
        # Step 1: Map dish to food items using ingredient_mapper
        ingredient_mappings = ingredient_mapper.map_dish_to_food_items(
            db, dish_name, diet_type, meal_id
        )
        
        if not ingredient_mappings:
            # Fallback: Keep original meal, try to parse from dish_name directly
            print(f"  ⚠ No ingredients mapped, using fallback calculation")
            calculated_meals.append(_fallback_meal_calculation(meal, m_target_cal, m_target_p, m_target_c, m_target_f))
            continue
        
        # Step 2: Build work items with ROLE CLASSIFICATION for human-realistic portions
        work_items = []
        beverage_items = []  # Beverages are tracked separately (excluded from optimization)
        
        for idx, (ing_name, food_item, match_type) in enumerate(ingredient_mappings):
            # Classify ingredient role based on name and position
            role = ingredient_mapper.classify_ingredient_role(ing_name, position_in_dish=idx)
            constraints = ingredient_mapper.get_portion_constraints(role)
            
            # Log role classification
            ingredient_mapper.log_role_classification(ing_name, role, constraints)
            
            if food_item:
                # Use DB macros (per 100g)
                density = {
                    "p": float(food_item.protein_g) / 100,
                    "c": float(food_item.carb_g) / 100,
                    "f": float(food_item.fat_g) / 100,
                    "cal": float(food_item.calories_kcal) / 100
                }
                # Use original name for display, not DB name (e.g. "Upma" not "Semolina")
                display_name = ing_name.title()
            else:
                # Use fallback macros
                fallback = ingredient_mapper.get_fallback_macros(ing_name)
                density = {k: v/100 for k, v in fallback.items()}
                display_name = ing_name.title()
            
            # Handle beverages differently - fixed size, excluded from optimization
            if role == "beverage":
                serving_size = ingredient_mapper.get_beverage_serving_size(ing_name)
                beverage_items.append({
                    "name": display_name,
                    "weight": serving_size,
                    "density": density,
                    "role": role,
                    "fixed": True
                })
            else:
                # Start with default weight for the role
                work_items.append({
                    "name": display_name,
                    "weight": constraints["default"],
                    "density": density,
                    "role": role,
                    "constraints": constraints,
                    "scalable": constraints["scalable"]
                })
        
        if not work_items and not beverage_items:
            calculated_meals.append(_fallback_meal_calculation(meal, m_target_cal, m_target_p, m_target_c, m_target_f))
            continue
        
        # Calculate beverage contributions (fixed, not optimized)
        bev_cal = bev_p = bev_c = bev_f = 0
        for b in beverage_items:
            bev_cal += b["weight"] * b["density"]["cal"]
            bev_p += b["weight"] * b["density"]["p"]
            bev_c += b["weight"] * b["density"]["c"]
            bev_f += b["weight"] * b["density"]["f"]
        
        # Adjust targets to account for beverage contribution
        adj_target_cal = m_target_cal - bev_cal
        adj_target_p = m_target_p - bev_p
        adj_target_c = m_target_c - bev_c
        adj_target_f = m_target_f - bev_f
        
        # Ensure adjusted targets are positive
        adj_target_cal = max(adj_target_cal, 100)
        adj_target_p = max(adj_target_p, 5)
        adj_target_c = max(adj_target_c, 10)
        adj_target_f = max(adj_target_f, 5)
        
        if beverage_items:
            print(f"    📢 Beverages fixed: {bev_cal:.0f}kcal | Remaining target: {adj_target_cal:.0f}kcal")
        
        # Step 3: Iterative Optimization with ROLE CONSTRAINTS
        # Only PRIMARY items scale freely; SECONDARY has limited scaling; SIDE is mostly fixed
        # INCREASED ITERATIONS & DYNAMIC RELAXATION for Stricter 5% Compliance
        
        max_iterations = 50
        learning_rate = 0.15
        tgt_tolerance = 0.04 # Target 4% internally to safely hit 5%
        
        # Dynamic Constraint Relaxation Loop
        # If we fail to converge, we relax constraints and try again
        constraint_multipliers = [1.0, 1.2, 1.5, 2.0, 3.0] 
        
        best_weights = {w["name"]: w["weight"] for w in work_items}
        min_error = float('inf')
        
        for relaxation in constraint_multipliers:
            
            for i in range(max_iterations):
                # Calculate current totals (excluding beverages)
                cur_p = cur_c = cur_f = cur_cal = 0
                for w in work_items:
                    wt = w["weight"]
                    cur_p += wt * w["density"]["p"]
                    cur_c += wt * w["density"]["c"]
                    cur_f += wt * w["density"]["f"]
                    cur_cal += wt * w["density"]["cal"]
                
                if cur_cal == 0: break
                
                # Check Convergence (Strict 5%)
                # We calculate deviations based on Adjusted Target (which excludes fixed beverages)
                cal_dev_p = (cur_cal - adj_target_cal) / adj_target_cal if adj_target_cal > 0 else 0
                p_dev_p = (cur_p - adj_target_p) / adj_target_p if adj_target_p > 0 else 0
                c_dev_p = (cur_c - adj_target_c) / adj_target_c if adj_target_c > 0 else 0
                f_dev_p = (cur_f - adj_target_f) / adj_target_f if adj_target_f > 0 else 0
                
                # STRICT check: Calorie within 5% AND Macros within 5%
                if (abs(cal_dev_p) < tgt_tolerance and 
                    abs(p_dev_p) < tgt_tolerance and 
                    abs(c_dev_p) < tgt_tolerance and 
                    abs(f_dev_p) < tgt_tolerance):
                    # converged!
                    min_error = 0 # Mark as perfect
                    break
                
                # Track best state
                total_error = abs(cal_dev_p) + abs(p_dev_p) + abs(c_dev_p) + abs(f_dev_p)
                if total_error < min_error:
                    min_error = total_error
                    best_weights = {w["name"]: w["weight"] for w in work_items}

                # Phase 1: Calorie Scaling (Master Constraint)
                cal_deficit = adj_target_cal - cur_cal
                
                scalable_items = [w for w in work_items if w.get("scalable", True)]
                if scalable_items:
                    total_scalable_weight = sum(w["weight"] for w in scalable_items)
                    if total_scalable_weight > 0:
                        for w in scalable_items:
                            proportion = w["weight"] / total_scalable_weight
                            cal_per_g = w["density"]["cal"]
                            if cal_per_g > 0:
                                # Scale to close calorie gap
                                additional_weight = (cal_deficit * proportion) / cal_per_g
                                w["weight"] += additional_weight * 0.9
                
                # Phase 2: Macro Balancing
                # Only if calories are somewhat close (within 10%)
                if abs(cal_dev_p) < 0.10:
                    for w in work_items:
                        if not w.get("scalable", True): continue
                        
                        role = w["role"]
                        factor = 1.0
                        
                        # PRIMARY: Adjust for biggest deviations
                        if role == "primary":
                            if p_dev_p < -tgt_tolerance: factor += learning_rate
                            elif p_dev_p > tgt_tolerance: factor -= learning_rate
                            
                            if c_dev_p < -tgt_tolerance: factor += learning_rate
                            elif c_dev_p > tgt_tolerance: factor -= learning_rate

                        # SECONDARY: Support role
                        elif role == "secondary":
                            if p_dev_p < -tgt_tolerance*2: factor += learning_rate * 0.5
                            if f_dev_p < -tgt_tolerance*2: factor += learning_rate * 0.5
                        
                        w["weight"] *= factor

                # Apply Constraints (Relaxed by outer loop)
                for w in work_items:
                    base_constraints = w.get("constraints", {"min": 50, "max": 300})
                    max_limit = base_constraints["max"] * relaxation
                    min_limit = base_constraints["min"]
                    w["weight"] = max(min_limit, min(max_limit, w["weight"]))
            
            # End Inner Loop
            if min_error == 0: break # Converged perfectly
        
        # Restore best found weights
        for w in work_items:
            if w["name"] in best_weights:
                w["weight"] = best_weights[w["name"]]
        
        # --- PHASE 4: MATH-FIRST ENFORCEMENT ("Anyhow" Mode) ---
        # Explicitly force the math to line up, overriding previous constraints if needed.
        _force_macro_compliance(work_items, adj_target_cal, adj_target_p, adj_target_c, adj_target_f)
        # -------------------------------------------------------

        # Step 4: Format final output with human-readable portions
        
        # Step 4: Format final output with human-readable portions
        portion_parts = []
        final_p = final_c = final_f = final_cal = 0
        
        # First add food items
        for w in work_items:
            final_weight = round(w["weight"] / 5) * 5  # Round to nearest 5g
            constraints = w.get("constraints", {"min": 50, "max": 300})
            final_weight = max(constraints["min"], min(constraints["max"], final_weight))
            
            # Clean name: take first part before comma to avoid long USDA descriptions
            # e.g. "Chicken, breast, raw" -> "Chicken" (or maybe we want "Chicken breast"?)
            # USDA usually format: "Term, Qualifier, Qualifier". 
            # Let's take first 2 terms if short, or just first.
            # actually simplified: just split by comma and take first part.
            clean_name = w['name'].split(',')[0].strip()
            portion_parts.append(f"{int(final_weight)}g {clean_name}")
            
            final_p += final_weight * w["density"]["p"]
            final_c += final_weight * w["density"]["c"]
            final_f += final_weight * w["density"]["f"]
            final_cal += final_weight * w["density"]["cal"]
        
        # Then add beverages (with ml notation)
        for b in beverage_items:
            clean_name = b['name'].split(',')[0].strip()
            portion_parts.append(f"{int(b['weight'])}ml {clean_name}")
            
            final_p += b["weight"] * b["density"]["p"]
            final_c += b["weight"] * b["density"]["c"]
            final_f += b["weight"] * b["density"]["f"]
            final_cal += b["weight"] * b["density"]["cal"]
        
        # Build calculated meal
        calculated_meal = meal.copy()
        # Use + as separator as requested
        calculated_meal["portion_size"] = " + ".join(portion_parts)
        calculated_meal["nutrients"] = {
            "p": round(final_p, 1),
            "c": round(final_c, 1),
            "f": round(final_f, 1),
            "cal": round(final_cal)
        }
        
        # Log the calculation result
        print(f"  ✓ {meal_id.upper()} Calculated: {final_cal:.0f}kcal | P:{final_p:.1f}g | C:{final_c:.1f}g | F:{final_f:.1f}g")
        print(f"    └── Portions: {calculated_meal['portion_size']}")
        
        calculated_meals.append(calculated_meal)
    
    print("\n" + "=" * 70)
    return calculated_meals


def _fallback_meal_calculation(meal: Dict, target_cal: float, target_p: float, target_c: float, target_f: float) -> Dict:
    """
    Fallback calculation when ingredient mapping fails.
    Uses generic macro ratios to estimate portions.
    """
    dish_name = meal.get("dish_name", "Mixed Meal")
    
    # Create a simple fallback portion
    fallback_meal = meal.copy()
    fallback_meal["portion_size"] = f"~400g {dish_name}"
    fallback_meal["nutrients"] = {
        "p": round(target_p, 1),
        "c": round(target_c, 1),
        "f": round(target_f, 1),
        "cal": round(target_cal)
    }
    
    return fallback_meal




def optimize_meal_portions_iterative(db: Session, meals: List[Dict], targets: Dict, fitness_goal: str = None) -> List[Dict]:
    """
    Iteratively optimizes portion sizes to match Macro Targets (P/C/F) while keeping Calories strict.
    Logic:
    1. Identify 'Role' of each ingredient (Protein Source, Carb Source, Fat Source).
    2. Loop:
       a. Scale ALL items to hit Calorie Target exactly (Highest Priority).
       b. Check Maco Deviations.
       c. If P is low, boost Protein Source weight relative to others.
       d. If C is high, cut Carb Source weight.
       e. Re-normalize to Calories.
    3. Converges on a distribution that hits Calories AND optimized Macros.
    """
    print(f"\n[Post-Process] Smart Macro Balancing (Iterative)...")
    
    meal_ratios = get_meal_ratios_by_fitness_goal(fitness_goal)
    total_target_cal = float(targets.get("calories", 2000))
    total_target_p = float(targets.get("protein", 150))
    total_target_c = float(targets.get("carbs", 200))
    total_target_f = float(targets.get("fat", 60))
    
    optimized_meals = []
    
    for meal in meals:
        meal_id = meal.get("meal_id", "meal").lower()
        if meal_id not in meal_ratios: meal_ratios[meal_id] = 0.25
        
        # Meal Targets
        ratio = meal_ratios[meal_id]
        m_target_cal = total_target_cal * ratio
        m_target_p = total_target_p * ratio
        m_target_c = total_target_c * ratio
        m_target_f = total_target_f * ratio
        
        # Analyze Ingredients
        p_str = meal.get("portion_size", "")
        dish_name = meal.get("dish_name", "")
        if not re.search(r'\d', p_str):
            parse_input = f"{dish_name}, {p_str}"
        else:
            parse_input = p_str
            
        analysis = calculate_meal_macros_from_db(db, parse_input)
        items = analysis["items"] # List of {name, weight, density: {p,c,f,cal}}
        
        if not items:
            optimized_meals.append(meal)
            continue
            
        # 1. Classify Items
        # Create a working list with mutable weights
        # Role: 0=Mix, 1=Protein, 2=Carb, 3=Fat
        work_items = []
        for item in items:
            d = item["density"]
            # Identify dominant macro by caloric contribution
            cal_p = d['p'] * 4
            cal_c = d['c'] * 4
            cal_f = d['f'] * 9
            total_dense = cal_p + cal_c + cal_f
            
            role = "mix"
            if total_dense > 0:
                if cal_p > 0.4 * total_dense: role = "protein"
                elif cal_c > 0.5 * total_dense: role = "carb"
                elif cal_f > 0.5 * total_dense: role = "fat"
            
            work_items.append({
                "name": item["name"],
                "weight": item["weight"],
                "density": d,
                "role": role,
                "orig_weight": item["weight"]
            })
            
        # 2. Optimization Loop
        iterations = 15
        learning_rate = 0.15 # How aggressively to adjust ratios
        
        for i in range(iterations):
            # A. Calculate Current Totals
            cur_p = cur_c = cur_f = cur_cal = 0
            for w in work_items:
                wt = w["weight"]
                cur_p += wt * w["density"]["p"]
                cur_c += wt * w["density"]["c"]
                cur_f += wt * w["density"]["f"]
                cur_cal += wt * w["density"]["cal"]
            
            if cur_cal == 0: break
            
            # B. STRICT CALORIE NORMALIZATION (Master Constraint)
            # We ALWAYS prioritize calories.
            cal_scale = m_target_cal / cur_cal
            for w in work_items:
                w["weight"] *= cal_scale
            
            # Recalculate after normalization
            cur_p = cur_c = cur_f = cur_cal = 0
            for w in work_items:
                wt = w["weight"]
                cur_p += wt * w["density"]["p"]
                cur_c += wt * w["density"]["c"]
                cur_f += wt * w["density"]["f"]
                cur_cal += wt * w["density"]["cal"]
                
            # C. Check Deviations & Adjust Ratios
            # We adjust weights of specific groups relative to others
            # If Protein is low, boost Protein items. The next Calorie Norm will pull others down.
            
            if i < iterations - 1: # Don't adjust on last step, just norm calories
                p_dev = (cur_p - m_target_p) / m_target_p if m_target_p > 0 else 0
                c_dev = (cur_c - m_target_c) / m_target_c if m_target_c > 0 else 0
                f_dev = (cur_f - m_target_f) / m_target_f if m_target_f > 0 else 0
                
                # Apply nudges based on role
                for w in work_items:
                    role = w["role"]
                    factor = 1.0
                    
                    if role == "protein":
                        if p_dev < -0.05: factor += learning_rate # Boost protein source
                        elif p_dev > 0.05: factor -= learning_rate
                    elif role == "carb":
                        if c_dev < -0.05: factor += learning_rate
                        elif c_dev > 0.05: factor -= learning_rate
                    elif role == "fat":
                        if f_dev < -0.05: factor += learning_rate
                        elif f_dev > 0.05: factor -= learning_rate
                    
                    # Clamp constraints? Ensure weight doesn't vanish or explode too much
                    # relative to original recipe capability (heuristic)
                    w["weight"] *= factor
                    if w["weight"] < 10: w["weight"] = 10 # Minimum 10g
        
        # 3. Final Formatting
        new_items_str = []
        final_p = final_c = final_f = final_cal = 0
        
        for w in work_items:
            final_weight = round(w["weight"] / 5) * 5 # Round to nearest 5g
            if final_weight < 5: final_weight = 5
            
            new_items_str.append(f"{int(final_weight)}g {w['name']}")
            
            final_p += final_weight * w["density"]["p"]
            final_c += final_weight * w["density"]["c"]
            final_f += final_weight * w["density"]["f"]
            final_cal += final_weight * w["density"]["cal"]
            
        # Update Meal Object
        new_meal = meal.copy()
        new_meal["portion_size"] = ", ".join(new_items_str)
        new_meal["nutrients"] = {
            "p": round(final_p, 1),
            "c": round(final_c, 1),
            "f": round(final_f, 1),
            "cal": round(final_cal)
        }
        
        optimized_meals.append(new_meal)
        
    return optimized_meals


def _detect_targeted_meals(prompt: str) -> List[str]:
    """
    Detect which meals are explicitly targeted by the prompt.
    Returns list of meal_ids (e.g., ['breakfast', 'dinner']).
    If empty, implies global update (no specific target).
    """
    prompt_lower = prompt.lower()
    targets = []
    
    # Keyword mapping
    keywords = {
        "breakfast": ["breakfast", "morning"],
        "lunch": ["lunch", "afternoon"],
        "dinner": ["dinner", "night", "evening", "supper"],
        "snacks": ["snack", "snacks", "tea", "coffee"]
    }
    
    for meal_id, terms in keywords.items():
        if any(term in prompt_lower for term in terms):
            targets.append(meal_id)
            
    return targets



def adjust_portions_to_fix_deviations(db: Session, meals: List[Dict], targets: Dict, deviations: Dict) -> List[Dict]:
    """
    Smart Adjustment Logic (Iterative + Scoring):
    1. Identify 'Locked' metrics (OK status) vs 'Deviating' metrics.
    2. Adjust portions of specific items to fix deviations WITHOUT breaking locked metrics.
    3. Uses scoring to select best candidates that maximize fix and minimize side effects.
    """
    print("\n[Smart Adjustment] Attempting to fix macro deviations (Iterative)...")
    
    adjusted_meals = [m.copy() for m in meals]
    
    # Allow multiple passes to converge
    max_passes = 3
    
    for pass_idx in range(max_passes):
        # 1. Re-Calculate Current State & Deviations
        current_totals = {"p": 0, "c": 0, "f": 0, "cal": 0}
        for m in adjusted_meals:
            # We must recalc from portion_size string to be sure of density/macros
            parsed = calculate_meal_macros_from_db(db, m["portion_size"])
            # Update meal nutrients temporarily for tracking
            m["nutrients"] = {
                "p": parsed["total_p"],
                "c": parsed["total_c"],
                "f": parsed["total_f"],
                "cal": parsed["total_cal"]
            }
            for k in current_totals: current_totals[k] += m["nutrients"][k]

        current_deviations = []
        locked_metrics = []
        
        for metric, target in targets.items():
            val = current_totals[metric[:1]] if metric != "calories" else current_totals["cal"]
            diff = val - target
            pct = (diff / target) * 100 if target > 0 else 0
            
            if abs(pct) > 5:
                current_deviations.append({"metric": metric, "diff": diff, "pct": pct, "target": target})
            else:
                locked_metrics.append(metric)
        
        if not current_deviations:
            print("  [Smart Adj] All metrics OK. Converged.")
            break
            
        # Sort deviations by magnitude (Absolute %)
        current_deviations.sort(key=lambda x: abs(x["pct"]), reverse=True)
        
        # Fix the biggest deviation
        focus = current_deviations[0]
        metric = focus["metric"]  # 'protein', 'carbs', 'fat', 'calories'
        deficit = -focus["diff"] # If diff is negative (Low), deficit is positive (Need to add)
        
        print(f"  [Pass {pass_idx+1}] Focusing on {metric.upper()} (Deficit: {deficit:.1f}, {focus['pct']:.1f}%)")
        
        # Determine Per-Meal Target
        meal_target = deficit / len(adjusted_meals)
        
        for i, meal in enumerate(adjusted_meals):
            p_str = meal.get("portion_size", "")
            analysis = calculate_meal_macros_from_db(db, p_str)
            items = analysis["items"]
            if not items: continue
            
            # Identify Candidates (items that provide the target metric)
            m_key = metric[:1] if metric != "calories" else "cal"
            candidates = [x for x in items if x["density"][m_key] > 0]
            
            if not candidates: continue
            
            # --- CANDIDATE SCORING ---
            scored_candidates = []
            for cand in candidates:
                d = cand["density"]
                primary_impact = d[m_key]
                
                # Base Score: Efficiency
                score = primary_impact * 10 
                
                # Penalties/Bonuses based on SIDE EFFECTS on OTHER deviations
                for other_dev in current_deviations:
                    if other_dev["metric"] == metric: continue
                    
                    om = other_dev["metric"]
                    om_key = om[:1] if om != "calories" else "cal"
                    om_impact = d[om_key]
                    
                    # If we are ADDING weight (Deficit > 0):
                    if deficit > 0:
                        if other_dev["diff"] < 0: # Other is ALSO LOW
                             score += om_impact * 5 # Bonus! Helps other low metric
                        else: # Other is HIGH
                             score -= om_impact * 20 # Penalty! Worsens high metric
                    else: # We are REMOVING weight
                        if other_dev["diff"] > 0: # Other is HIGH
                            score += om_impact * 5 # Bonus! Helps reduce high metric
                        else: # Other is LOW
                            score -= om_impact * 20 # Penalty! Worsens low metric

                scored_candidates.append((score, cand))
            
            # Pick best candidate
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            best_cand = scored_candidates[0][1]
            
            # Calculate Delta
            # Dampening factor 0.8 to avoid overshooting
            needed_change = (meal_target / best_cand["density"][m_key]) * 0.8
            
            # Apply Limit (Don't remove more than we have, don't add crazy amounts)
            old_w = best_cand["weight"]
            new_w = max(10, old_w + needed_change) # Minimal 10g
            if new_w > 500: new_w = 500 # Max 500g cap
            
            actual_delta = new_w - old_w
            best_cand["weight"] = new_w
            
            # --- CALORIE COMPENSATION ---
            # Only if Calories are Locked (OK) and we just disrupted them
            if "calories" in locked_metrics:
                cal_delta = actual_delta * best_cand["density"]["cal"]
                if abs(cal_delta) > 10:
                    needed_offset = -cal_delta
                    
                    # Find compensators (items NOT the one we just changed)
                    compensators = [x for x in items if x["name"] != best_cand["name"]]
                    if compensators:
                        # Score Compensators
                        scored_comps = []
                        for comp in compensators:
                            s = 0
                            cd = comp["density"]
                            
                            # Score based on how changing this affects OTHER deviations
                            for dev in current_deviations:
                                km = dev["metric"]
                                k_key = km[:1] if km != "calories" else "cal"
                                k_imp = cd[k_key]
                                
                                if needed_offset > 0: # Adding weight
                                    if dev["diff"] < 0: s += k_imp * 10
                                    else: s -= k_imp * 20
                                else: # Removing weight
                                    if dev["diff"] > 0: s += k_imp * 10
                                    else: s -= k_imp * 20
                            
                            scored_comps.append((s, comp))
                        
                        scored_comps.sort(key=lambda x: x[0], reverse=True)
                        best_comp = scored_comps[0][1]
                        
                        if best_comp["density"]["cal"] > 0:
                            comp_delta = needed_offset / best_comp["density"]["cal"]
                            cw = best_comp["weight"] + comp_delta
                            best_comp["weight"] = max(10, cw)

            # Reconstruct Meal Strings
            new_parts = []
            final_nut = {"p": 0, "c": 0, "f": 0, "cal": 0}
            
            for item in items:
                w = item["weight"]
                qty = round(w / 5) * 5
                if qty < 5: qty = 5
                
                new_parts.append(f"{int(qty)}g {item['name']}")
                
                final_nut["p"] += qty * item["density"]["p"]
                final_nut["c"] += qty * item["density"]["c"]
                final_nut["f"] += qty * item["density"]["f"]
                final_nut["cal"] += qty * item["density"]["cal"]
                
            new_meal = meal.copy()
            new_meal["portion_size"] = " + ".join(new_parts)
            new_meal["nutrients"] = {k: round(v, 1) for k, v in final_nut.items()}
            new_meal["nutrients"]["cal"] = round(final_nut["cal"]) # int for calories
            
            adjusted_meals[i] = new_meal
            
    return adjusted_meals



def _detect_update_type(prompt: str) -> dict:
    """
    Detect what type of update the user is requesting.
    Returns dict with 'update_type' and 'property' keys.
    """
    prompt_lower = prompt.lower()
    
    # Property keywords
    property_keywords = {
        "portion": ["portion", "size", "amount", "quantity", "gram", "g", "ml", "increase", "decrease", "more", "less"],
        "dish": ["dish", "food", "meal", "recipe"],
        "alternative": ["alternative", "substitute", "swap"],
        "guideline": ["guideline", "tip", "suggestion", "instruction", "pair", "serve"]
    }
    
    detected_property = None
    for prop, keywords in property_keywords.items():
        if any(kw in prompt_lower for kw in keywords):
            detected_property = prop
            break
    
    # Determine if full regeneration or property update
    full_change_keywords = ["change to", "different", "new", "replace with", "give me"]
    property_update_keywords = ["update", "modify", "adjust", "add", "remove"]
    
    is_property_update = any(kw in prompt_lower for kw in property_update_keywords)
    is_full_change = any(kw in prompt_lower for kw in full_change_keywords)
    
    # If property detected and property update keywords, it's a property update
    if detected_property and (is_property_update or not is_full_change):
        update_type = "property"
    elif is_full_change or "different" in prompt_lower:
        update_type = "full"
    else:
        update_type = "unclear"
    
    return {
        "update_type": update_type,
        "property": detected_property
    }


def generate_meal_plan(db: Session, user_id: int, custom_prompt: str = None, excluded_items_override: List[str] = None):
    """
    Main orchestrator for meal plan generation.
    
    Requirements fulfilled:
    1. Create 4 meals from food_items table
    2. Dish name format: Main (veg/non-veg) + Accompaniment [region] + Side
    3. Portion sizes in grams/ml
    4. Compare generated vs target macros (±5%)
    5. Calorie split: 35% breakfast, 30% lunch, 25% dinner, 10% snacks
    6. 2-2 alternatives and guidelines
    7. Custom prompt: search DB first, then LLM
    8. Update only affected meal card on custom prompt
    9. Veg/non-veg labeling
    10. Meal-type specific food suggestions
    """
    logger.info(f"Starting meal plan generation for user {user_id}")
    
    # 1. Get User Profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        raise ValueError("UserProfile not found.")

    # 2. Refresh Nutrition Targets
    age = getattr(profile.user, 'age', 25) if profile.user else 25
    gender = getattr(profile.user, 'gender', 'male') if profile.user else 'male'
    
    # A. Calculate BASELINE Targets (Maintenance/Goal)
    base_targets = nutrition_service.calculate_daily_targets(
        weight=profile.weight,
        height=profile.height,
        age=age,
        gender=gender,
        activity_level=profile.activity_level,
        fitness_goal=profile.fitness_goal,
        diet_type=profile.diet_type,
        weight_goal=profile.weight_goal
    )
    
    # B. Get EFFECTIVE Targets (Buffer/Feast Adjustments)
    from app.services.social_event_service import get_effective_daily_targets
    import datetime
    
    targets = get_effective_daily_targets(
        db, user_id, base_targets, datetime.date.today()
    )
    
    # C. Update Profile? 
    # CRITICAL: Only update UserProfile if targets match Baseline (No Event Active)
    # This protects the user's "True Reference" from being overwritten by temporary buffer drops.
    if not getattr(profile, 'skip_macro_calculation', False):
        # We only save to profile if these are the "Normal" targets
        # Or... we strictly separate "Plan Targets" from "Profile Targets".
        # For now, let's keep Profile as the "Source of Truth for Normal Days".
        
        is_baseline = (targets['calories'] == base_targets['calories'])
        if is_baseline:
            profile.calories = targets['calories']
            profile.protein = targets['protein']
            profile.fat = targets['fat']
            profile.carbs = targets['carbs']
            db.commit()
        else:
            logger.info(f"Social Buffer Active: Using effective targets ({targets['calories']} vs {base_targets['calories']}) without overwriting profile.")
    
    # 3. Detect Regeneration Scenario (no custom prompt but existing plan exists)
    is_regeneration_for_variety = False
    excluded_previous_items = []
    
    if excluded_items_override:
         # Explicit override from regenerate_meal_plan
         is_regeneration_for_variety = True
         excluded_previous_items = excluded_items_override
         logger.info(f"Variety mode (History): Excluding {len(excluded_previous_items)} items.")
    elif not custom_prompt:
        # Check if user has an existing plan
        existing_meals = crud_meal_plan.get_meal_plan(db, user_id)
        if existing_meals:
            # This is a regeneration without custom prompt - user wants variety
            is_regeneration_for_variety = True
            excluded_previous_items = extract_food_items_from_previous_plan(db, profile.id)
            if excluded_previous_items:
                logger.info(f"Variety mode (Standard): Excluding {len(excluded_previous_items)} items from previous plan")
                logger.info(f"Using temperature: 0.7 for increased variety")
    
    # 4. Validate Custom Prompt
    custom_food_context = ""
    if custom_prompt:
        # 3a. Check for non-veg requests from vegetarian users
        if profile.diet_type and profile.diet_type.lower() in ["veg", "vegetarian"]:
            non_veg_keywords = ["chicken", "mutton", "fish", "egg", "meat", "pork", "beef", "lamb", 
                               "prawn", "shrimp", "crab", "lobster", "bacon", "ham", "sausage", 
                               "salmon", "tuna", "turkey", "keema", "tikka"]
            prompt_lower = custom_prompt.lower()
            for keyword in non_veg_keywords:
                if keyword in prompt_lower:
                    raise ValueError(f"Your diet type is 'Vegetarian'. You cannot add non-veg items like '{keyword}'. Please update your diet type to 'Non-Veg' in your profile first.")
        
        # 3b. Validate prompt with LLM
        llm_service.validate_user_prompt(custom_prompt, context_type="diet")
        
        # 3c. Search for mentioned foods in our database
        food_names = extract_food_names_from_prompt(custom_prompt)
        found_foods = []
        not_found_foods = []
        
        for name in food_names:
            item = find_food_item_by_name(db, name, profile.diet_type)
            if item:
                veg_label = "(veg)" if item.diet_type == "veg" else "(non-veg)"
                found_foods.append(
                    f"- {item.name} {veg_label} | Per 100g: P:{float(item.protein_g):.1f}g, "
                    f"C:{float(item.carb_g):.1f}g, F:{float(item.fat_g):.1f}g, {int(item.calories_kcal)}kcal"
                )
            else:
                not_found_foods.append(name)
        
        if found_foods:
            custom_food_context = f"\n[REQUESTED FOODS FROM DATABASE]\n" + "\n".join(found_foods)
        if not_found_foods:
            custom_food_context += f"\n[NOT IN DATABASE - LLM MAY SUGGEST]\n" + ", ".join(not_found_foods)
    
    # 5. Prepare Context (Region, Food Items)
    user_country = profile.country or "India"
    region = get_region_from_country(user_country)
    is_veg_user = profile.diet_type and profile.diet_type.lower() in ["veg", "vegetarian"]
    
    # Get food items filtered by diet_type, region, country (with limit for optimization)
    food_items = get_food_items_filtered(
        db=db,
        diet_type=profile.diet_type,
        region=region,
        country=user_country,
        limit=50  # Limit to 50 items for token optimization
    )
    
    # Format food list for LLM (Categorized by meal type with veg/non-veg labels)
    food_context = _format_food_items_enhanced(food_items, region, is_veg_user)
    
    # Get existing plan for context (for custom prompt updates)
    plan_context = ""
    existing_meals_db = []
    if custom_prompt:
        plan_context = _get_existing_plan_context(db, profile.id)
        # Fetch actual meal objects to restore if LLM is lazy
        existing_meals_db = crud_meal_plan.get_meal_plan(db, user_id)
    
    # 6. Calculate Meal Calorie Targets (35%, 30%, 25%, 10%)
    total_cal = float(profile.calories)
    total_protein = float(profile.protein)
    total_carbs = float(profile.carbs)
    total_fat = float(profile.fat)
    
    # --- DEBUG: Show User Profile Targets ---
    print("\n" + "=" * 70)
    print("           USER PROFILE TARGETS (from DB after recalculation)")
    print("=" * 70)
    print(f"  User ID: {user_id} | Profile ID: {profile.id}")
    print(f"  Weight: {profile.weight}kg | Height: {profile.height}cm | Goal: {profile.fitness_goal}")
    print(f"  Diet Type: {profile.diet_type} | Activity: {profile.activity_level}")
    print("-" * 70)
    print(f"  TARGETS → Calories: {total_cal:.0f} kcal | Protein: {total_protein:.1f}g | Carbs: {total_carbs:.1f}g | Fat: {total_fat:.1f}g")
    print("=" * 70 + "\n")
    
    # 6. Get Meal Ratios based on fitness goal
    meal_ratios = get_meal_ratios_by_fitness_goal(profile.fitness_goal)
    logger.info(f"Using meal ratios for '{profile.fitness_goal}': {meal_ratios}")
    
    meal_targets = {
        "breakfast": {"cal": int(total_cal * meal_ratios["breakfast"]), "p": round(total_protein * meal_ratios["breakfast"], 1), 
                      "c": round(total_carbs * meal_ratios["breakfast"], 1), "f": round(total_fat * meal_ratios["breakfast"], 1)},
        "lunch": {"cal": int(total_cal * meal_ratios["lunch"]), "p": round(total_protein * meal_ratios["lunch"], 1),
                  "c": round(total_carbs * meal_ratios["lunch"], 1), "f": round(total_fat * meal_ratios["lunch"], 1)},
        "dinner": {"cal": int(total_cal * meal_ratios["dinner"]), "p": round(total_protein * meal_ratios["dinner"], 1),
                   "c": round(total_carbs * meal_ratios["dinner"], 1), "f": round(total_fat * meal_ratios["dinner"], 1)},
        "snacks": {"cal": int(total_cal * meal_ratios["snacks"]), "p": round(total_protein * meal_ratios["snacks"], 1),
                   "c": round(total_carbs * meal_ratios["snacks"], 1), "f": round(total_fat * meal_ratios["snacks"], 1)}
    }
    
    # Build the enhanced prompt
    system_prompt = """You are a nutritionist. Output ONLY valid JSON. No explanation."""
    
    display_diet = "Veg + Non-Veg"
    mix_instruction = "Mix of Vegetarian and Non-Veg dishes. Ensure a balance."

    if profile.diet_type == 'veg':
       display_diet = "Vegetarian"
       mix_instruction = """
       STRICT VEGETARIAN RULE:
       - Every single meal must be 100% Vegetarian.
       - NO meat, NO fish, NO eggs.
       - Use Paneer, Curd, Lentils, Beans, Tofu, Milk as protein sources.
       """
    elif profile.diet_type == 'non_veg': 
       display_diet = "Non-Vegetarian"
       mix_instruction = """
       STRICT NON-VEGETARIAN RULE:
       - Every single meal (Breakfast, Lunch, Dinner, Snacks) MUST contain a Non-Veg item.
       - Use Chicken, Eggs, Fish, Meat, etc.
       - Pair with vegetarian sides (Rice, Roti, Salad), but the MAIN protein must be Non-Veg.
       - START with a Non-Veg dish (e.g., "Chicken Curry", "Scrambled Eggs") for every slot.
       """
    else: # 'both'
       display_diet = "Veg + Non-Veg"
       mix_instruction = """
       MIXED DIET RULE:
       - Strictly provide a balanced mix of Vegetarian and Non-Vegetarian meals.
       - Target: 2 Vegetarian meals AND 2 Non-Vegetarian meals per day.
       - Example: Breakfast (Non-Veg), Lunch (Veg), Dinner (Non-Veg), Snacks (Veg).
       """
    
    preservation_instruction = ""
    if custom_prompt and plan_context:
        preservation_instruction = """
IMPORTANT (UPDATE MODE):
You are updating an EXISTING meal plan based on the user's custom request.

PROPERTY-LEVEL UPDATES:
If the user asks to update a SPECIFIC property of a meal (portion, dish, alternative, etc.):
1. Identify the meal and property to update
2. Update ONLY that specific property
3. Keep ALL other properties of that meal EXACTLY the same as shown in Current Plan
4. Keep all other meals completely unchanged

ADD / REMOVE INSTRUCTIONS:
- If user says "ADD X": APPEND it to the existing `dish_name` and `portion_size`.
  Example: "Add Apple" -> Dish="Old Dish + 1 Apple", Portion="Old Portion, 1 Apple"
  DO NOT REPLACE the existing meal unless explicit.
- If user says "REMOVE X": Remove it from `dish_name` and `portion_size`.

Property update examples:
- "Change scrambled eggs portion to 300g" → Update ONLY portion_size for breakfast, adjust nutrients
- "Add oatmeal as alternative" → Update ONLY alternatives array
- "Change lunch to grilled chicken" → Update dish_name and portion_size, recalculate nutrients

FULL MEAL REPLACEMENT:
If user asks to completely replace a meal ("Give me different breakfast"):
1. Generate entirely NEW meal for that slot
2. Keep all other meals unchanged

CRITICAL: PRESERVE all properties not mentioned. When updating portion_size, recalculate nutrients.
"""
    
    # Variety instruction for regeneration without custom prompt
    variety_instruction = ""
    if is_regeneration_for_variety and excluded_previous_items:
        import datetime
        current_time_seed = datetime.datetime.now().strftime("%H%M%S")
        
        variety_instruction = f"""
CRITICAL (VARIETY MODE - Fresh Regeneration #{current_time_seed}):
The user wants COMPLETELY NEW and DIFFERENT meal options. Be CREATIVE and DIVERSE.

DO NOT use these items from their previous plan:
{', '.join(excluded_previous_items)}

STRICT REQUIREMENTS:
- Suggest DIFFERENT main dishes/curries/proteins than before
- Use DIFFERENT cooking styles (e.g., if previous had curry, try dry/roasted/grilled)
- Vary the cuisine within the region (e.g., South Indian, North Indian, Bengali, etc.)
- Think of UNCOMMON but authentic dishes, not just popular ones
- You can use similar bases (rice/roti) but PRIMARY dishes MUST be completely different

CREATIVITY BOOST:
- Consider seasonal vegetables
- Mix traditional and fusion options
- Include different protein sources (dal varieties, paneer, tofu, eggs, different meats)
- Vary grain types (brown rice, quinoa, millet, regular rice)

Be adventurous while maintaining nutritional targets!
"""
    
    # Regional context instruction - Provide region-specific guidance
    regional_context_instruction = f"""
=== REGIONAL CONTEXT ===
User Region: {region}
User Country: {user_country}

CRITICAL: Prioritize {region} cuisine and cooking styles. Use authentic {region} dish names 
and traditional food combinations. Ensure meals reflect the culinary culture of {region}.
"""
    
    # Add region-specific dish format examples
    if region == "India":
        region_dish_examples = """
Examples for India:
- "Palak Paneer (veg) + Jeera Rice + Cucumber Salad"
- "Dal Tadka (veg) + 2 Roti + Mixed Salad"
- "Masala Dosa (veg) + Sambar + Coconut Chutney"
- "Chicken Curry (non-veg) + Steamed Rice + Raita"
"""
    elif region == "Asia":
        region_dish_examples = """
Examples for Asia:
- "Pad Thai (non-veg) + Jasmine Rice + Papaya Salad"
- "Stir-fried Tofu (veg) + Brown Rice + Bok Choy"
- "Teriyaki Chicken (non-veg) + Steamed Rice + Miso Soup"
- "Vegetable Ramen (veg) + Edamame + Pickled Vegetables"
"""
    elif region in ["Europe", "North America"]:
        region_dish_examples = f"""
Examples for {region}:
- "Grilled Chicken Breast (non-veg) + Mashed Potatoes + Steamed Broccoli"
- "Quinoa Salad (veg) + Chickpeas + Mixed Greens"
- "Baked Salmon (non-veg) + Sweet Potato + Green Beans"
- "Veggie Burger (veg) + Sweet Potato Fries + Coleslaw"
"""
    elif region == "Africa":
        region_dish_examples = """
Examples for Africa:
- "Jollof Rice (veg) + Fried Plantain + Coleslaw"
- "Grilled Tilapia (non-veg) + Ugali + Sukuma Wiki"
- "Injera with Lentils (veg) + Spicy Vegetables + Salad"
- "Peri-Peri Chicken (non-veg) + Rice + Mixed Salad"
"""
    elif region == "South America":
        region_dish_examples = """
Examples for South America:
- "Black Bean Stew (veg) + Rice + Farofa"
- "Grilled Steak (non-veg) + Chimichurri + Roasted Vegetables"
- "Quinoa Bowl (veg) + Corn + Avocado Salad"
- "Ceviche (non-veg) + Sweet Potato + Mixed Greens"
"""
    elif region == "Australia/Oceania":
        region_dish_examples = """
Examples for Australia/Oceania:
- "Grilled Barramundi (non-veg) + Roasted Vegetables + Garden Salad"
- "Veggie Pie (veg) + Mashed Peas + Coleslaw"
- "BBQ Chicken (non-veg) + Potato Salad + Corn on Cob"
- "Lentil Curry (veg) + Rice + Raita"
"""
    else:
        # Fallback
        region_dish_examples = """
Examples:
- "Main Protein (veg/non-veg) + Grain/Starch + Vegetables"
"""

    user_prompt_text = f"""
# ROLE (Persona)
You are a professional Nutritionist and Meal Planner.
Your job is to SELECT DISHES - we will calculate portions and nutrients automatically.

# CONTEXT
- Diet Type: {display_diet}
- Region: {region}
- Available Foods:
{food_context[:1500]}

# TASK (Goal)
Select 4 meals (Breakfast, Lunch, Dinner, Snacks) using the available foods.
Custom user requirements: {custom_prompt if custom_prompt else "None"}

# CONSTRAINTS (Formatting & Instructions)
{mix_instruction}
{preservation_instruction}
{variety_instruction}
{plan_context if custom_prompt else ""}

=== DISH NAMING FORMAT ===
Format: "Main Dish (veg/non-veg) + Accompaniment + Side"
{region_dish_examples}

=== OUTPUT JSON (SIMPLIFIED) ===
You only need to provide dish selection. We calculate nutrients automatically.
Strictly output ONLY valid JSON:
{{{{
  "meal_plan": [
    {{
      "meal_id": "breakfast",
      "label": "Breakfast",
      "is_veg": true,
      "dish_name": "Poha (veg) + Curd + Apple",
      "alternatives": ["Upma (veg)", "Idli (veg)"],
      "guidelines": ["Add peanuts for protein", "Pair with green tea"]
    }},
    {{
      "meal_id": "lunch",
      "label": "Lunch",
      "is_veg": true,
      "dish_name": "...",
      "alternatives": ["...", "..."],
      "guidelines": ["...", "..."]
    }},
    {{
      "meal_id": "dinner",
      "label": "Dinner",
      "is_veg": true,
      "dish_name": "...",
      "alternatives": ["...", "..."],
      "guidelines": ["...", "..."]
    }},
    {{
      "meal_id": "snacks",
      "label": "Snacks",
      "is_veg": true,
      "dish_name": "...",
      "alternatives": ["...", "..."],
      "guidelines": ["...", "..."]
    }}
  ]
}}}}

RULES: 
- Use authentic {region} food names
- Include (veg/non-veg) label in dish_name
- DO NOT include "portion_size" or "nutrients" - we calculate those automatically
- Output JSON only."""
    
    # 6. Call LLM (with Retry Logic)
    # Use higher temperature for variety mode to encourage creative alternatives
    llm_temperature = 0.7 if is_regeneration_for_variety else 0.1
    
    max_retries = 2
    current_attempt = 0
    is_valid_plan = False
    feedback_prompt = ""
    
    while current_attempt < max_retries:
        current_attempt += 1
        logger.info(f"Calling LLM for meal plan generation (Attempt {current_attempt}/{max_retries})...")
        
        # Append feedback if retrying
        current_user_prompt = user_prompt_text
        if feedback_prompt:
             current_user_prompt += f"\n\nIMPORTANT FEEDBACK FROM PREVIOUS ATTEMPT:\n{feedback_prompt}\nPLEASE FIX THESE ISSUES."
             logger.info(f"Retrying with feedback: {feedback_prompt}")

        response_data = llm_service.call_llm_json(
            system_prompt=system_prompt,
            user_prompt=current_user_prompt,
            temperature=llm_temperature,
            max_tokens=12000
        )
        
        if not response_data or "meal_plan" not in response_data:
            if current_attempt < max_retries:
                logger.warning("LLM returned invalid JSON. Retrying...")
                continue
            else:
                raise ValueError("Failed to generate a valid meal plan. Please try again.")
            
        generated_meals = response_data["meal_plan"]
        
        # --- SMART MERGE: Restore Lazy / Non-Targeted Output ---
        # Detect targeted meals globally for optimization logic
        targeted_meals = []
        if custom_prompt:
            targeted_meals = _detect_targeted_meals(custom_prompt)
            
        if existing_meals_db and generated_meals:
            # Convert DB meals to dict for easy lookup
            existing_map = {m.meal_id.lower(): m for m in existing_meals_db}
            
            if targeted_meals:
                print(f"[Strict Preserve] Targeted Update detected for: {targeted_meals}")
            
            for i, meal in enumerate(generated_meals):
                m_id = meal.get("meal_id", "").lower()
                d_name = meal.get("dish_name", "").strip()
                
                # CONDITION 1: Lazy Output detection
                is_lazy = False
                if len(d_name) < 3 or "..." in d_name or "dish name" in d_name.lower():
                    is_lazy = True
                
                # CONDITION 2: Strict Preservation (Force Restore if not targeted)
                should_force_restore = False
                if targeted_meals and m_id not in targeted_meals:
                    should_force_restore = True
                    
                if (is_lazy or should_force_restore) and m_id in existing_map:
                    # RESTORE from DB
                    orig = existing_map[m_id]
                    reason = "Targeted Update (Locked)" if should_force_restore else "Lazy LLM Output"
                    # Only log once per request ideally, but acceptable here
                    # print(f"[Smart Merge] Restoring '{m_id}' from DB. Reason: {reason}")
                    
                    p_val = float(orig.nutrients.get("p", 0))
                    c_val = float(orig.nutrients.get("c", 0))
                    f_val = float(orig.nutrients.get("f", 0))
                    cal_val = (p_val * 4) + (c_val * 4) + (f_val * 9)
                    
                    restored_meal = {
                        "meal_id": orig.meal_id,
                        "label": orig.label,
                        "is_veg": orig.is_veg,
                        "dish_name": orig.dish_name,
                        "portion_size": orig.portion_size,
                        "nutrients": {
                            "p": p_val,
                            "c": c_val,
                            "f": f_val,
                            "cal": cal_val
                        },
                        "alternatives": orig.alternatives,
                        "guidelines": orig.guidelines
                    }
                    generated_meals[i] = restored_meal

        if generated_meals:
            # ===============================================================
            # PHASE 2: BACKEND CALCULATION (Two-Phase Architecture)
            # ===============================================================
            # LLM has selected dishes. Now we calculate portions and nutrients.
            try:
                # Use the new two-phase calculation approach
                generated_meals = calculate_portions_from_dishes(
                    db=db, 
                    meals=generated_meals, 
                    targets=targets, 
                    diet_type=profile.diet_type,
                    fitness_goal=profile.fitness_goal
                )
            except Exception as e:
                logger.error(f"Two-Phase calculation error: {e}")
                # Fallback to old method if new one fails
                try:
                    generated_meals = optimize_meal_portions_iterative(db, generated_meals, targets, profile.fitness_goal)
                except Exception as e2:
                    logger.error(f"Fallback calculation also failed: {e2}")
            
            # Recalculate Totals for Validation
            total_metrics = {"p": 0, "c": 0, "f": 0, "cal": 0}
            for item in generated_meals:
                nutrients = item.get("nutrients", {})
                total_metrics["p"] += float(nutrients.get("p", 0))
                total_metrics["c"] += float(nutrients.get("c", 0))
                total_metrics["f"] += float(nutrients.get("f", 0))
                total_metrics["cal"] += float(nutrients.get("cal", 0))
            
            # Final Validation Logging
            final_generated_totals = {
                "calories": total_metrics["cal"],
                "protein": total_metrics["p"],
                "carbs": total_metrics["c"],
                "fat": total_metrics["f"]
            }
            is_valid, deviations = validate_macro_deviation(final_generated_totals, targets)
            
            # --- DEBUG: Show Target vs Backend-Calculated Comparison ---
            print("\n" + "=" * 70)
            print("       BACKEND CALCULATED VALUES vs USER PROFILE TARGETS")
            print("=" * 70)
            print(f"{'METRIC':<12} | {'PROFILE TARGET':<15} | {'CALCULATED':<15} | {'DEVIATION':<13}| {'STATUS':<6}")
            print("-" * 70)
            
            for key in ["calories", "protein", "carbs", "fat"]:
                target_val = targets.get(key, 0)
                gen_val = final_generated_totals.get(key, 0)
                
                # Deviation %
                dev_pct = 0
                if target_val > 0:
                    dev_pct = ((gen_val - target_val) / target_val) * 100
                    
                status = "✓ OK" if abs(dev_pct) <= 5 else "✗ EXCEED" if dev_pct > 0 else "✗ LOW"
                
                print(f"{key.upper():<12} | {target_val:<15.1f} | {gen_val:<15.1f} | {abs(dev_pct):<7.1f} % | {status}")
            
            print("-" * 70)
            print(f"OVERALL VALIDATION: {'✓ PASS' if is_valid else '✗ FAIL'} (tolerance: ±5%)")
            print("=" * 70)
            
            if is_valid:
                logger.info("Validation passed.")
                is_valid_plan = True
                break
            else:
                # --- SMART ADJUSTMENT (2nd Attempt) ---
                # Strategy: If validation fails, try to mathematically adjust portions
                # to fix the specific deviations without breaking the good ones.
                if current_attempt < max_retries:
                    logger.info("Validation failed. Attempting Smart Adjustment...")
                    try:
                        adjusted_meals = adjust_portions_to_fix_deviations(
                            db=db,
                            meals=generated_meals,
                            targets=targets,
                            deviations=deviations
                        )
                        
                        # Re-calculate totals for adjusted meals
                        total_metrics_adj = {"p": 0, "c": 0, "f": 0, "cal": 0}
                        for item in adjusted_meals:
                            nutrients = item.get("nutrients", {})
                            total_metrics_adj["p"] += float(nutrients.get("p", 0))
                            total_metrics_adj["c"] += float(nutrients.get("c", 0))
                            total_metrics_adj["f"] += float(nutrients.get("f", 0))
                            total_metrics_adj["cal"] += float(nutrients.get("cal", 0))
                        
                        final_adj_totals = {
                            "calories": total_metrics_adj["cal"],
                            "protein": total_metrics_adj["p"],
                            "carbs": total_metrics_adj["c"],
                            "fat": total_metrics_adj["f"]
                        }
                        
                        is_valid_adj, deviations_adj = validate_macro_deviation(final_adj_totals, targets)
                        
                        if is_valid_adj:
                            logger.info("Smart Adjustment SUCCESS! Validation passed.")
                            generated_meals = adjusted_meals
                            is_valid_plan = True
                            
                            # Log success
                            print("\n" + "=" * 70)
                            print("       SMART ADJUSTMENT SUCCESS (2nd Attempt)")
                            print("=" * 70)
                            print(f"{'METRIC':<12} | {'PROFILE TARGET':<15} | {'ADJUSTED':<15} | {'DEVIATION':<13}| {'STATUS':<6}")
                            print("-" * 70)
                            for key in ["calories", "protein", "carbs", "fat"]:
                                target_val = targets.get(key, 0)
                                gen_val = final_adj_totals.get(key, 0)
                                dev_pct = ((gen_val - target_val) / target_val * 100) if target_val > 0 else 0
                                status = "✓ OK" if abs(dev_pct) <= 5 else "✗ FAIL"
                                print(f"{key.upper():<12} | {target_val:<15.1f} | {gen_val:<15.1f} | {abs(dev_pct):<7.1f} % | {status}")
                            print("=" * 70)
                            break
                        else:
                            logger.warning("Smart Adjustment failed to fully resolve deviations.")
                            # Continue to next retry loop (LLM regeneration) if needed
                            
                    except Exception as e:
                        logger.error(f"Smart Adjustment error: {e}")

                # Feedback for next LLM attempt (if we didn't break)
                feedback_parts = []
                for k, v in deviations.items():
                    if not v["within_tolerance"]:
                        direction = "Reduce" if v["deviation_pct"] > 0 else "Increase"
                        feedback_parts.append(f"{direction} {k} (off by {v['deviation_pct']}%)")
                
                feedback_prompt = f"Validation failed. Issues: {', '.join(feedback_parts)}. "
                if current_attempt < max_retries:
                    logger.warning(f"Validation failed attempt {current_attempt}: {feedback_prompt}") 
            
    # End Loop
    
    # 8. Save to DB (Process the final attempt)
    db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).delete()
    
    saved_entries = []
    total_metrics = {"p": 0, "c": 0, "f": 0, "cal": 0}

    for item in generated_meals:
        # --- STRICT DB ENFORCEMENT START ---
        # Recalculate nutrients from the final portion string to ensure DB consistency
        # This overrides any LLM-estimated or optimization-drifted values
        try:
            db_analysis = calculate_meal_macros_from_db(db, item.get("portion_size", ""))
            
            # Override nutrients with strict DB values
            item["nutrients"] = {
                "p": round(db_analysis["total_p"], 1),
                "c": round(db_analysis["total_c"], 1),
                "f": round(db_analysis["total_f"], 1),
                "cal": round(db_analysis["total_cal"])
            }
            # Log the override
            # print(f"  🔒 Strict DB Enforcement for {item.get('meal_id')}: {item['nutrients']}")
        except Exception as e:
            logger.error(f"Failed to enforce DB consistency for {item.get('meal_id')}: {e}")
        # --- STRICT DB ENFORCEMENT END ---

        nutrients = item.get("nutrients", {})
        
        p = float(nutrients.get("p", 0))
        c = float(nutrients.get("c", 0))
        f = float(nutrients.get("f", 0))
        cal = (p * 4) + (c * 4) + (f * 9)
        
        total_metrics["p"] += p
        total_metrics["c"] += c
        total_metrics["f"] += f
        total_metrics["cal"] += cal
        
        meal_id = item.get("meal_id", "meal")
        default_label = meal_id.capitalize() if meal_id else "Meal"
        
        # Determine is_veg from dish_name if not provided
        dish_name = item.get("dish_name", "")
        is_veg_from_name = "(veg)" in dish_name.lower() and "(non-veg)" not in dish_name.lower()
        default_is_veg = is_veg_user if is_veg_user else is_veg_from_name
        
        meal_entry = MealPlan(
            user_profile_id=profile.id,
            meal_id=meal_id,
            label=item.get("label") or default_label,
            is_veg=item.get("is_veg") if item.get("is_veg") is not None else default_is_veg,
            dish_name=dish_name,
            portion_size=item.get("portion_size", ""),
            nutrients={"p": p, "c": c, "f": f},
            alternatives=item.get("alternatives", [])[:2],
            guidelines=item.get("guidelines", [])[:2]
        )
        db.add(meal_entry)
        saved_entries.append(meal_entry)
    
    # Update Profile with Generated Totals
    profile.calories = total_metrics["cal"]
    profile.protein = total_metrics["p"]
    profile.carbs = total_metrics["c"]
    profile.fat = total_metrics["f"]
    profile.skip_macro_calculation = True 
    
    db.commit()
    
    # Final Validation Logging
    final_generated_totals = {
        "calories": total_metrics["cal"],
        "protein": total_metrics["p"],
        "carbs": total_metrics["c"],
        "fat": total_metrics["f"]
    }
    is_valid, deviations = validate_macro_deviation(final_generated_totals, targets)
    
    # --- DEBUG: Show Target vs Generated Comparison ---
    print("\n" + "=" * 70)
    print("        LLM GENERATED VALUES vs USER PROFILE TARGETS")
    print("=" * 70)
    print(f"{'METRIC':<12} | {'PROFILE TARGET':<15} | {'LLM GENERATED':<15} | {'DEVIATION':<10} | STATUS")
    print("-" * 70)
    for key, data in deviations.items():
        status = "✓ OK" if data["within_tolerance"] else "✗ EXCEED"
        target = data['target']
        generated = data['generated']
        dev_pct = data.get('deviation_pct', 0)
        print(f"{key.upper():<12} | {target:<15.1f} | {generated:<15.1f} | {dev_pct:<8.1f}% | {status}")
    print("-" * 70)
    overall = "✓ PASS" if is_valid else "✗ FAIL"
    print(f"OVERALL VALIDATION: {overall} (tolerance: ±5%)")
    print("=" * 70 + "\n")
    
    if not is_valid:
        logger.warning(f"Generated meal plan exceeds ±5% macro deviation tolerance: {deviations}")
    
    # 9. Build Response
    response_items = []
    for m in saved_entries:
        response_items.append(MealItem(
            meal_id=m.meal_id,
            label=m.label,
            is_veg=m.is_veg,
            dish_name=m.dish_name,
            portion_size=m.portion_size,
            nutrients=NutrientDetail(p=m.nutrients['p'], c=m.nutrients['c'], f=m.nutrients['f']),
            alternatives=m.alternatives,
            guidelines=m.guidelines
        ))

    # Verify and log detailed macros
    try:
        _verify_and_log_macros(db, saved_entries)
    except Exception as e:
        logger.error(f"Failed to verify macros: {e}")

    # 10. Save Snapshot to History
    try:
        snapshot = [
            {
                "meal_id": m.meal_id,
                "label": m.label,
                "is_veg": m.is_veg,
                "dish_name": m.dish_name,
                "portion_size": m.portion_size,
                "nutrients": m.nutrients,
                "alternatives": m.alternatives,
                "guidelines": m.guidelines
            }
            for m in saved_entries
        ]
        
        history_entry = MealPlanHistory(
            user_profile_id=profile.id,
            meal_plan_snapshot=snapshot,
            change_reason="GENERATION"
        )
        db.add(history_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save meal plan history: {e}")

    return MealPlanResponse(
        user_profile_id=profile.id,
        daily_targets=NutrientTotals(
            calories=targets['calories'],
            protein=targets['protein'],
            carbs=targets['carbs'],
            fat=targets['fat']
        ),
        daily_generated_totals=NutrientTotals(
            calories=total_metrics['cal'],
            protein=total_metrics['p'],
            carbs=total_metrics['c'],
            fat=total_metrics['f']
        ),
        meal_plan=response_items,
        verification=f"Generated {len(response_items)} meals. Deviation valid: {is_valid}"
    )


def regenerate_meal_plan(db: Session, user_id: int):
    """
    Regenerate meal plan with strict variety enforcement.
    Excludes items from the last 7 generations (history).
    """
    logger.info(f"Regenerating meal plan for user {user_id} with history-based variety.")
    
    # Fetch profile to get correct profile_id
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        raise ValueError("UserProfile not found.")
        
    # 1. Fetch History (Last 7 entries)
    history = db.query(MealPlanHistory)\
        .filter(MealPlanHistory.user_profile_id == profile.id)\
        .order_by(MealPlanHistory.created_at.desc())\
        .limit(8)\
        .all()
    
    excluded_items = []
    common_sides = ['salad', 'raita', 'curd', 'cucumber', 'chutney', 'pickle', 'yogurt', 
                    'fruit', 'banana', 'apple', 'tea', 'coffee', 'water', 'roti', 'rice',
                    'chapati', 'naan', 'paratha', 'steamed rice', 'jeera rice', 'mixed salad']

    if history:
        # User said "until regenerating 8 times... before 8 times it should not repeat".
        # If we have < 8 history items, exclude ALL of them.
        # If we have >= 8, we can start repeating (or maybe the 9th one can match the 1st one?)
        # Logic: Collect items from the retrieved history (which is limit 8).
        # Actually, let's just exclude everything we find in the last 7-8 entries.
        
        for record in history:
            snapshot = record.meal_plan_snapshot
            if not snapshot:
                continue
                
            # snapshot is a list of dicts or JSON
            if isinstance(snapshot, str):
                try:
                    snapshot = json.loads(snapshot)
                except:
                    continue
            
            for meal in snapshot:
                dish_name = meal.get('dish_name', '')
                
                # Extract main items (same logic as before)
                if dish_name:
                    parts = dish_name.split('+')
                    for part in parts:
                        clean_part = part.strip()
                        clean_part = clean_part.replace('(veg)', '').replace('(non-veg)', '').strip()
                        
                        if clean_part.lower() in common_sides:
                            continue
                        if len(clean_part) < 4:
                            continue
                        if clean_part.replace(' ', '').isdigit():
                            continue
                            
                        # Remove leading numbers/units
                        clean_part = re.sub(r'^\d+(\.\d+)?\s*(g|ml|pcs|piece)?\s*', '', clean_part).strip()

                        if clean_part and not any(side in clean_part.lower() for side in common_sides):
                            excluded_items.append(clean_part)

    excluded_items = list(set(excluded_items))
    logger.info(f"Found {len(excluded_items)} items to exclude based on history.")
    
    # 2. Call Standard Generation with Exclusion Context
    # We can reuse generate_meal_plan but we need to inject the exclusions.
    # Since generate_meal_plan has logic to check "previous plan", we should probably override or extend it.
    # Refactoring generate_meal_plan to accept an explicit exclusion list would be cleanest.
    # But to avoid breaking existing signatures too much, let's pass a special custom_prompt string?
    # No, that's hacky.
    # Let's Modify generate_meal_plan to accept `excluded_items_override`.
    
    return generate_meal_plan(db, user_id, custom_prompt=None, excluded_items_override=excluded_items)



def _format_food_items_enhanced(food_items: List[FoodItem], region: str, is_veg_user: bool) -> str:
    """
    Format food items categorized by meal type with enhanced information.
    Optimized to reduce token usage while maintaining quality.
    Includes veg/non-veg labels and per-100g macro values.
    """
    
    categories = {
        "BREAKFAST": [],
        "LUNCH": [],
        "DINNER": [],
        "SNACK": []
    }
    
    for f in food_items:
        m_type = f.meal_type.lower() if f.meal_type else ""
        
        # Veg/Non-veg label
        veg_label = "(veg)" if f.diet_type == "veg" else "(non-veg)"
        
        # Regional marker
        regional_marker = f"[{f.region}]" if f.region else ""
        
        # Per 100g values
        entry = (
            f"- {f.name} {veg_label} {regional_marker} | "
            f"Per 100g: P:{float(f.protein_g):.1f}g, C:{float(f.carb_g):.1f}g, "
            f"F:{float(f.fat_g):.1f}g, {int(f.calories_kcal)}kcal"
        )
        
    # Categorize by meal type
        if "breakfast" in m_type:
            categories["BREAKFAST"].append((f.diet_type, entry))
        if "lunch" in m_type:
            categories["LUNCH"].append((f.diet_type, entry))
        if "dinner" in m_type:
            categories["DINNER"].append((f.diet_type, entry))
        if "snack" in m_type:
            categories["SNACK"].append((f.diet_type, entry))
    
    # Format output with optimized limits per category (reduced from 8 to 6)
    output_parts = []
    
    # Add regional context header
    output_parts.append(f"[AVAILABLE {region.upper()} FOODS]")
    
    for title, items in categories.items():
        if not items:
            continue
            
        final_list = []
        if is_veg_user:
            # Take top 6 (reduced from 8 for token optimization)
            final_list = [x[1] for x in items[:6]]
        else:
            # Enforce Mix: Take 3 Veg and 3 Non-Veg (reduced from 4+4)
            veg_items = [x[1] for x in items if x[0] == 'veg']
            non_veg_items = [x[1] for x in items if x[0] == 'non_veg']
            
            # Interleave or combine to get variety
            # Take up to 3 non-veg, fill rest with veg
            selected_non_veg = non_veg_items[:3]
            remaining_slots = 6 - len(selected_non_veg)
            selected_veg = veg_items[:remaining_slots]
            
            final_list = selected_non_veg + selected_veg
            
        output_parts.append(f"\n[{title} ITEMS]")
        output_parts.append("\n".join(final_list))
    
    return "\n".join(output_parts)


def _get_existing_plan_context(db: Session, profile_id: int) -> str:
    """Get existing meal plan with detailed property breakdown for updates."""
    existing = db.query(MealPlan).filter(MealPlan.user_profile_id == profile_id).all()
    if not existing:
        return ""
    
    context_parts = ["=== CURRENT MEAL PLAN ==="]
    for m in existing:
        nutrients = m.nutrients or {}
        
        # Format alternatives and guidelines
        alternatives_str = str(m.alternatives) if m.alternatives else "[]"
        guidelines_str = str(m.guidelines) if m.guidelines else "[]"
        
        # Structured property breakdown
        meal_details = f"""
[{m.label.upper()}]
  meal_id: "{m.meal_id}"
  dish_name: "{m.dish_name}"
  portion_size: "{m.portion_size}"
  nutrients: {{ p: {nutrients.get('p', 0)}g, c: {nutrients.get('c', 0)}g, f: {nutrients.get('f', 0)}g }}
  alternatives: {alternatives_str}
  guidelines: {guidelines_str}
  is_veg: {m.is_veg}
"""
        context_parts.append(meal_details.strip())
    
    context_parts.append("\nTo update a property: copy meal structure, modify ONLY requested property.")
    return "\n".join(context_parts)





def _verify_and_log_macros(db: Session, meal_plans: List[MealPlan]):
    """
    Logs a detailed comparison table of Generated vs Actual(DB) macros.
    """
    print("\n" + "="*80)
    print(f"{'MACRO VERIFICATION REPORT':^80}")
    print("="*80)
    
    total_gen = {"p": 0, "c": 0, "f": 0, "cal": 0}
    total_actual = {"p": 0, "c": 0, "f": 0, "cal": 0}
    
    for meal in meal_plans:
        print(f"\nMEAL: {meal.label.upper()}")
        print(f"DISH: {meal.dish_name}")
        print(f"PORTION: {meal.portion_size}")
        
        # Generated values
        gen_p = float(meal.nutrients.get('p', 0))
        gen_c = float(meal.nutrients.get('c', 0))
        gen_f = float(meal.nutrients.get('f', 0))
        gen_cal = (gen_p * 4) + (gen_c * 4) + (gen_f * 9)
        
        total_gen["p"] += gen_p
        total_gen["c"] += gen_c
        total_gen["f"] += gen_f
        total_gen["cal"] += gen_cal

    # Calculate actual from DB using shared helper (SAME LOGIC)
        analysis = calculate_meal_macros_from_db(db, meal.portion_size)
        
        actual_p = analysis["total_p"]
        actual_c = analysis["total_c"]
        actual_f = analysis["total_f"]
        actual_cal = analysis["total_cal"]
        
        found_items = []
        for item in analysis["items"]:
            found_items.append(f"{item['weight']}g {item['name']} ({item['source']})")
        
        total_actual["p"] += actual_p
        total_actual["c"] += actual_c
        total_actual["f"] += actual_f
        total_actual["cal"] += actual_cal

        # Print comparison table
        print("-" * 80)
        print(f"{'METRIC':<10} | {'GENERATED':<12} | {'ACTUAL (DB)':<12} | {'DIFF':<10} | {'%DEV':<8}")
        print("-" * 80)
        
        def print_row(name, gen, act):
            diff = gen - act
            pct = (abs(diff) / act * 100) if act > 0 else 0
            status = "✓" if pct <= 5 else "✗"
            print(f"{name:<10} | {gen:<12.1f} | {act:<12.1f} | {diff:<+10.1f} | {pct:<6.1f}% {status}")
        
        print_row("Protein", gen_p, actual_p)
        print_row("Carbs", gen_c, actual_c)
        print_row("Fat", gen_f, actual_f)
        print_row("Calories", gen_cal, actual_cal)
        print("-" * 80)
        print(f"Items: {', '.join(found_items)}")

    # Print daily totals
    print("\n" + "="*80)
    print(f"{'DAILY TOTALS':^80}")
    print("="*80)
    print(f"{'METRIC':<10} | {'GENERATED':<12} | {'ACTUAL (DB)':<12} | {'DIFF':<10}")
    print("-" * 80)
    print(f"{'Protein':<10} | {total_gen['p']:<12.1f} | {total_actual['p']:<12.1f} | {total_gen['p']-total_actual['p']:<+10.1f}")
    print(f"{'Carbs':<10} | {total_gen['c']:<12.1f} | {total_actual['c']:<12.1f} | {total_gen['c']-total_actual['c']:<+10.1f}")
    print(f"{'Fat':<10} | {total_gen['f']:<12.1f} | {total_actual['f']:<12.1f} | {total_gen['f']-total_actual['f']:<+10.1f}")
    print(f"{'Calories':<10} | {total_gen['cal']:<12.0f} | {total_actual['cal']:<12.0f} | {total_gen['cal']-total_actual['cal']:<+10.0f}")
    print("="*80 + "\n")

def adjust_todays_meal_plan(db: Session, user_id: int, target_calories: int, completed_meals: List[str]):
    """
    Feast Mode Helper (Bidirectional):
    Adjusts the *remaining* meals for today to meet a new calorie target.
    - If target < planned: SCALES DOWN (Banking Phase)
    - If target > planned: SCALES UP (Restore Phase / Undo)
    
    Args:
        db: Database session
        user_id: User ID
        target_calories: The NEW effective daily target (e.g. 1800 or 2500)
        completed_meals: List of meal IDs already logged (e.g. ["breakfast", "lunch"])
    """
    # 1. Fetch User Profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        return {"error": "Profile not found"}
        
    # 2. Fetch Current Meal Plan
    plan_items = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()
    if not plan_items:
        return {"error": "No meal plan found for today"}
        
    # 3. Calculate Consumed & Remaining
    consumed_calories = 0
    remaining_items = []
    
    completed_norm = [m.lower() for m in completed_meals]
    
    def get_nutrient_val(nuts, keys):
        nuts = nuts or {}
        for k in keys:
            try:
                val = float(nuts.get(k) or 0)
                if val > 0: return val
            except (ValueError, TypeError):
                continue
        return 0.0

    def get_calories(item):
        nuts = item.nutrients or {}
        # Try direct keys
        cal = get_nutrient_val(nuts, ['calories', 'cal'])
        if cal > 0: return cal
        
        # Try calc from macros
        p = get_nutrient_val(nuts, ['protein', 'p'])
        c = get_nutrient_val(nuts, ['carbs', 'c'])
        f = get_nutrient_val(nuts, ['fat', 'f'])
        
        if p > 0 or c > 0 or f > 0:
            return (p * 4) + (c * 4) + (f * 9)
            
        return 0.0
    
    for item in plan_items:
        # Check if meal is completed
        cal = get_calories(item)
        if item.meal_id.lower() in completed_norm:
            consumed_calories += cal
        else:
            remaining_items.append(item)
            
    # 4. Calculate Budget & Difference
    # Goal: Target - Consumed = Remaining Budget
    remaining_budget = target_calories - consumed_calories
    
    # Calculate current planned calories for remaining items
    current_planned_calories = sum(get_calories(i) for i in remaining_items)
    
    # Difference (Positive = Needs more food, Negative = Needs less food)
    diff = remaining_budget - current_planned_calories 
    
    print(f"[MealAdjust] Target: {target_calories}, Consumed: {consumed_calories}, Budget: {remaining_budget}")
    print(f"[MealAdjust] Planned: {current_planned_calories}, Diff: {diff}")
    
    # Small threshold to avoid noise
    if abs(diff) < 20:
        return {"message": "No adjustment needed (Within threshold)", "diff": 0}
        
    if remaining_budget <= 200:
        return {"message": "Warning: Remaining budget is too low (<200kcal). Dangerous to adjust.", "diff": diff}

    # 5. Apply Scaling Strategy
    # Ratio > 1.0 (Scale Up), Ratio < 1.0 (Scale Down)
    if current_planned_calories > 0:
        ratio = remaining_budget / current_planned_calories
    else:
        ratio = 1.0
    
    # Safety Caps
    # Don't reduce below 50% (Starvation guard)
    # Don't increase above 200% (Gluttony guard / unrealistic portion)
    ratio = max(0.5, min(ratio, 2.0))
    
    changes_log = []
    import re

    def scale_portion_string(p_str, factor):
        # Regex for "100g", "200ml", "1.5 slice", "2 pcs"
        # We look for numbers at start of words
        return re.sub(r'\b(\d+(\.\d+)?)\b', lambda m: f"{float(m.group(1)) * factor:.0f}", p_str)

    
    for item in remaining_items:
        # Flexible Parsing
        original_cal = get_calories(item) # Re-use helper
             
        new_cal = original_cal * ratio
        
        # Scaling Factor for this item
        item_ratio = ratio 
        
        # Update Nutrients (Create new dict to ensure SQLAlchemy detects change in JSONB)
        current_nuts = dict(item.nutrients or {})
        
        # We must re-extract base macros to scale them
        p_val = get_nutrient_val(current_nuts, ['protein', 'p'])
        c_val = get_nutrient_val(current_nuts, ['carbs', 'c'])
        f_val = get_nutrient_val(current_nuts, ['fat', 'f'])
        
        # We standardize to full names on save
        current_nuts['calories'] = new_cal
        current_nuts['protein'] = p_val * item_ratio
        current_nuts['carbs'] = c_val * item_ratio
        current_nuts['fat'] = f_val * item_ratio
        
        # ALSO Update legacy keys if they exist to prevent CRUD reading stale data
        if 'p' in current_nuts: current_nuts['p'] = current_nuts['protein']
        if 'c' in current_nuts: current_nuts['c'] = current_nuts['carbs']
        if 'f' in current_nuts: current_nuts['f'] = current_nuts['fat']
        if 'cal' in current_nuts: current_nuts['cal'] = current_nuts['calories']
        
        item.nutrients = current_nuts
        flag_modified(item, "nutrients")
        
        # Update Portion Size String (Crucial for UI)
        new_portion = scale_portion_string(item.portion_size, item_ratio)
        
        changes_log.append(f"{item.meal_id}: {item.portion_size} -> {new_portion} ({original_cal:.0f} -> {new_cal:.0f} kcal)")
        
        item.portion_size = new_portion
        
    db.commit()
    
    return {
        "message": "Plan updated successfully",
        "diff_applied": current_planned_calories * (ratio - 1),
        "changes": changes_log
    }


def adjust_meals_with_llm(db: Session, user_id: int, target_calories: int, completed_meals: List[str]):
    """
    Feast Mode Agent: LLM-powered smart meal adjustment.
    
    Instead of uniformly scaling all meals by the same ratio, this function:
    1. Sends current meals + calorie delta to the LLM
    2. LLM decides per-meal adjustments (protects protein, reduces snacks first)
    3. Returns adjusted meals with per-meal notes explaining changes
    4. Falls back to ratio-based adjust_todays_meal_plan() if LLM fails
    
    Args:
        db: Database session
        user_id: User ID
        target_calories: The NEW effective daily target
        completed_meals: List of meal IDs already logged
    """
    from app.services import llm_service
    
    # 1. Fetch User Profile & Meal Plan
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        return {"error": "Profile not found"}
    
    plan_items = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()
    if not plan_items:
        return {"error": "No meal plan found"}
    
    # 2. Categorize meals
    completed_norm = [m.lower() for m in completed_meals]
    
    def get_nutrient_val(nuts, keys):
        nuts = nuts or {}
        for k in keys:
            try:
                val = float(nuts.get(k) or 0)
                if val > 0: return val
            except (ValueError, TypeError):
                continue
        return 0.0
    
    def get_calories(item):
        nuts = item.nutrients or {}
        p = get_nutrient_val(nuts, ['protein', 'p'])
        c = get_nutrient_val(nuts, ['carbs', 'c'])
        f = get_nutrient_val(nuts, ['fat', 'f'])
        return (p * 4) + (c * 4) + (f * 9)
    
    consumed_calories = 0
    remaining_items = []
    remaining_items_data = []
    
    for item in plan_items:
        cal = get_calories(item)
        if item.meal_id.lower() in completed_norm:
            consumed_calories += cal
        else:
            remaining_items.append(item)
            nuts = item.nutrients or {}
            remaining_items_data.append({
                "meal_id": item.meal_id,
                "label": item.label,
                "dish_name": item.dish_name,
                "portion_size": item.portion_size,
                "calories": round(cal),
                "protein": round(get_nutrient_val(nuts, ['protein', 'p']), 1),
                "carbs": round(get_nutrient_val(nuts, ['carbs', 'c']), 1),
                "fat": round(get_nutrient_val(nuts, ['fat', 'f']), 1),
            })
    
    remaining_budget = target_calories - consumed_calories
    current_planned = sum(d["calories"] for d in remaining_items_data)
    diff = remaining_budget - current_planned
    
    logger.info(f"[FeastAgent] Target: {target_calories}, Consumed: {consumed_calories}, " 
                f"Budget: {remaining_budget}, Planned: {current_planned}, Diff: {diff}")
    
    # Small threshold
    if abs(diff) < 20:
        return {"message": "No adjustment needed (within threshold)", "diff": 0}
    
    # 3. Build LLM Prompt
    direction = "REDUCE" if diff < 0 else "INCREASE"
    abs_diff = abs(round(diff))
    
    system_prompt = """You are a nutrition adjustment agent for a meal planning app.
Your job is to adjust the remaining meals to meet a new calorie target.

RULES:
1. PROTECT PROTEIN: Never reduce protein by more than 5%. Protein is sacred for muscle preservation.
2. REDUCE SNACKS FIRST: When cutting calories, reduce snack portions before touching main meals.
3. CARBS ARE FLEXIBLE: Carbs (rice, bread, roti) are the easiest to adjust without impacting satiety.
4. FAT IS SECONDARY: After carbs, adjust fat content slightly if needed.
5. KEEP DISH NAMES: Never change the dish itself, only adjust portion sizes and nutrients.
6. PROVIDE NOTES: For each adjusted meal, provide a short human-readable note explaining the change.

Respond in JSON format:
{
  "adjusted_meals": [
    {
      "meal_id": "breakfast",
      "portion_size": "updated portion string",
      "protein": 25.0,
      "carbs": 40.0,
      "fat": 10.0,
      "note": "Reduced rice from 150g to 100g (-80 kcal)"
    }
  ]
}"""

    meals_str = json.dumps(remaining_items_data, indent=2)
    
    user_prompt = f"""Current remaining meals:
{meals_str}

TASK: {direction} total calories by {abs_diff} kcal.
Current total: {current_planned} kcal → Target remaining: {remaining_budget} kcal.

Adjust each meal's portion_size, protein, carbs, and fat values accordingly.
Include a "note" for each meal explaining what changed.
Return ALL meals (even unchanged ones with note "No change needed")."""

    # 4. Call LLM
    try:
        response = llm_service.call_llm_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=4000
        )
        
        if not response or "adjusted_meals" not in response:
            raise ValueError("LLM returned invalid response")
        
        adjusted = response["adjusted_meals"]
        
        # 5. Apply LLM adjustments to DB
        meal_map = {item.meal_id.lower(): item for item in remaining_items}
        changes_log = []
        
        for adj in adjusted:
            m_id = adj.get("meal_id", "").lower()
            if m_id not in meal_map:
                continue
            
            item = meal_map[m_id]
            old_cal = get_calories(item)
            
            new_p = float(adj.get("protein", 0))
            new_c = float(adj.get("carbs", 0))
            new_f = float(adj.get("fat", 0))
            new_cal = (new_p * 4) + (new_c * 4) + (new_f * 9)
            
            # Update nutrients
            new_nuts = dict(item.nutrients or {})
            new_nuts['p'] = round(new_p, 1)
            new_nuts['c'] = round(new_c, 1)
            new_nuts['f'] = round(new_f, 1)
            new_nuts['protein'] = new_nuts['p']
            new_nuts['carbs'] = new_nuts['c']
            new_nuts['fat'] = new_nuts['f']
            new_nuts['calories'] = round(new_cal)
            if 'cal' in new_nuts:
                new_nuts['cal'] = new_nuts['calories']
            
            item.nutrients = new_nuts
            flag_modified(item, "nutrients")
            
            # Update portion size
            new_portion = adj.get("portion_size", item.portion_size)
            item.portion_size = new_portion
            
            # Update feast notes
            note = adj.get("note", "")
            if note:
                item.feast_notes = [note]
                flag_modified(item, "feast_notes")
            
            changes_log.append(f"{m_id}: {old_cal:.0f} → {new_cal:.0f} kcal | {note}")
        
        db.commit()
        
        logger.info(f"[FeastAgent] LLM adjustment applied: {changes_log}")
        return {
            "message": "Plan adjusted with smart LLM agent",
            "method": "llm",
            "diff_applied": diff,
            "changes": changes_log
        }
        
    except Exception as e:
        logger.warning(f"[FeastAgent] LLM adjustment failed ({e}), falling back to ratio-based")
        # Fallback to existing ratio-based method
        return adjust_todays_meal_plan(db, user_id, target_calories, completed_meals)


def estimate_food_calories(db: Session, food_descriptions: List[str]) -> Dict[str, float]:
    """
    Estimates scale/macros for user-described foods.
    1. Tries exact DB lookup via find_food_item_by_name()
    2. Falls back to VectorService semantic search
    3. Falls back to LLM estimation with rough macro split (handled by caller if this returns partial)
    
    Returns: { 
        "calories": float, 
        "protein": float, 
        "carbs": float, 
        "fat": float, 
        "items": [list of details] 
    }
    """
    total_cal = 0.0
    total_p = 0.0
    total_c = 0.0
    total_f = 0.0
    found_details = []
    
    vector_service = VectorService()
    
    for desc in food_descriptions:
        desc = desc.strip()
        if not desc: continue
        
        # 1. Try Exact/Partial DB Lookup
        food_item = find_food_item_by_name(db, desc)
        
        # 2. Try Vector Search if not found
        if not food_item:
            results = vector_service.search_food(desc, limit=1, threshold=0.6)
            if results:
                # Mock a FoodItem from payload
                payload = results[0]
                food_item = FoodItem(
                    name=payload.get('name', desc),
                    protein_g=payload.get('protein', 0),
                    carb_g=payload.get('carbs', 0),
                    fat_g=payload.get('fat', 0),
                    calories_kcal=payload.get('calories', 0),
                    serving_size_g=payload.get('serving_size', 100)
                )
        
        if food_item:
            # Assume 1 standard serving (approx 100g or 1 unit) if no qty specified
            # In a real app, we'd parse "2 slices" etc., but for now we assume 1.5x serving for "eating out" generosity
            multiplier = 1.0
            
            cal = float(food_item.calories_kcal) * multiplier
            p = float(food_item.protein_g) * multiplier
            c = float(food_item.carb_g) * multiplier
            f = float(food_item.fat_g) * multiplier
            
            total_cal += cal
            total_p += p
            total_c += c
            total_f += f
            
            found_details.append(f"{desc} (~{int(cal)} kcal)")
        else:
            # 3. Not found - Caller/LLM will have to guess, or we use a fallback average
            # Fallback: 250kcal per unidentified "item" (safe buffer)
            print(f"[Estimate] Could not find '{desc}', assuming generic 250kcal.")
            total_cal += 250
            total_p += 10
            total_c += 30
            total_f += 10
            found_details.append(f"{desc} (Est. 250 kcal)")

    return {
        "calories": total_cal,
        "protein": total_p,
        "carbs": total_c,
        "fat": total_f,
        "details": found_details
    }


def adjust_single_meal(db: Session, user_id: int, meal_id: str, override_info: Dict) -> Dict:
    """
    Replaces a single meal with user override info.
    
    Args:
        override_info: {
            dish_name: str,
            estimated_calories: float,
            estimated_macros: { p, c, f } (optional),
            reason: str
        }
        
    Returns:
        Result dict including the updated meal object.
    """
    # 1. Fetch Profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        return {"error": "Profile not found"}
        
    # 2. Prepare Update Data
    new_cal = float(override_info.get("estimated_calories", 0))
    macros = override_info.get("estimated_macros", {})
    
    # If macros missing, infer from calories using 40/30/30 split (rough estimate)
    if not macros or sum(macros.values()) == 0:
        p_cal = new_cal * 0.30
        c_cal = new_cal * 0.40
        f_cal = new_cal * 0.30
        mac_p = round(p_cal / 4, 1)
        mac_c = round(c_cal / 4, 1)
        mac_f = round(f_cal / 9, 1)
    else:
        mac_p = macros.get("p", 0)
        mac_c = macros.get("c", 0)
        mac_f = macros.get("f", 0)
        
    update_data = {
        "dish_name": override_info.get("dish_name", "User Adjusted Meal"),
        "portion_size": "User Estimated",
        "nutrients": {
            "p": mac_p, "c": mac_c, "f": mac_f,
            "protein": mac_p, "carbs": mac_c, "fat": mac_f,
            "calories": new_cal, "cal": new_cal
        },
        "guidelines": [f"Adjusted via AI Coach: {override_info.get('reason', 'Manual override')}"],
        "is_user_adjusted": True,
        "adjustment_note": f"{override_info.get('reason', 'Eating out')} ({int(new_cal)} kcal)"
    }
    
    # 3. Perform Update
    updated_meal = update_single_meal(db, profile.id, meal_id, update_data)
    
    if not updated_meal:
        return {"error": f"Meal '{meal_id}' not found in current plan"}
        
    # 4. Save to History (Snapshot)
    # We should grab the FULL plan now to save a coherent snapshot
    full_plan = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()
    try:
        snapshot = [
            {
                "meal_id": m.meal_id,
                "label": m.label,
                "dish_name": m.dish_name,
                "portion_size": m.portion_size,
                "nutrients": m.nutrients,
                "is_user_adjusted": m.is_user_adjusted,
                "adjustment_note": m.adjustment_note
            }
            for m in full_plan
        ]
        history_entry = MealPlanHistory(
            user_profile_id=profile.id,
            meal_plan_snapshot=snapshot,
            change_reason="USER_ADJUSTMENT"
        )
        db.add(history_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save history on adjustment: {e}")

    return {
        "message": f"Successfully updated {meal_id}",
        "meal": updated_meal,
        "calories": new_cal
    }


def skip_meal_and_redistribute(db: Session, user_id: int, meal_id: str, redistribute_to: List[str] = None, is_feast_day: bool = True):
    """
    Feast Mode: Skip a meal.
    
    - On FEAST DAY (is_feast_day=True): Redistribute freed calories to remaining meals
    - On BANKING DAY (is_feast_day=False): Just zero the meal (extra calories banked)
    
    Args:
        db: Database session
        user_id: User ID
        meal_id: The meal_id to skip (e.g. "snack")
        redistribute_to: Optional list of meal_ids to receive the calories (default: all remaining)
        is_feast_day: Whether today is the feast day (True) or a banking day (False)
    """
    from app.services import llm_service
    
    # 1. Fetch Profile & Plan
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        return {"error": "Profile not found"}
    
    plan_items = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()
    if not plan_items:
        return {"error": "No meal plan found"}
    
    # 2. Find the meal to skip
    meal_map = {item.meal_id.lower(): item for item in plan_items}
    skip_key = meal_id.lower()
    
    if skip_key not in meal_map:
        return {"error": f"Meal '{meal_id}' not found in plan"}
    
    skipped = meal_map[skip_key]
    
    # Calculate freed calories
    def get_nutrient_val(nuts, keys):
        nuts = nuts or {}
        for k in keys:
            try:
                val = float(nuts.get(k) or 0)
                if val > 0: return val
            except (ValueError, TypeError):
                continue
        return 0.0
    
    old_nuts = skipped.nutrients or {}
    freed_p = get_nutrient_val(old_nuts, ['protein', 'p'])
    freed_c = get_nutrient_val(old_nuts, ['carbs', 'c'])
    freed_f = get_nutrient_val(old_nuts, ['fat', 'f'])
    freed_cal = (freed_p * 4) + (freed_c * 4) + (freed_f * 9)
    
    if freed_cal < 10:
        return {"error": "Meal already has negligible calories"}
    
    # 3. Zero out skipped meal
    skipped.nutrients = {"p": 0, "c": 0, "f": 0, "protein": 0, "carbs": 0, "fat": 0, "calories": 0, "cal": 0}
    flag_modified(skipped, "nutrients")
    skipped.portion_size = "SKIPPED"
    
    # 4. Banking day — just zero meal, don't redistribute
    if not is_feast_day:
        skipped.feast_notes = [f"BANKED:{round(freed_cal)} kcal saved by skipping this meal"]
        flag_modified(skipped, "feast_notes")
        db.commit()
        return {"message": f"Skipped {meal_id} — {round(freed_cal)} kcal banked!", "freed_cal": round(freed_cal), "banked": True}
    
    # 5. Feast day — redistribute freed calories to remaining meals
    skipped.feast_notes = ["SKIPPED"]
    flag_modified(skipped, "feast_notes")
    
    # Determine receiving meals
    # Check completed meals from food logs
    from app.models.tracking import FoodLog
    from datetime import date as date_type
    today = date_type.today()
    logs = db.query(FoodLog).filter(FoodLog.user_id == user_id, FoodLog.date == today).all()
    completed_meals = list(set([l.meal_type.lower() for l in logs]))
    
    if redistribute_to:
        receiver_keys = [m.lower() for m in redistribute_to]
    else:
        # All remaining meals except skipped and completed
        receiver_keys = [
            k for k in meal_map.keys() 
            if k != skip_key and k not in completed_meals
        ]
    
    if not receiver_keys:
        db.commit()
        return {"message": f"Skipped {meal_id} but no remaining meals to redistribute to", "freed_cal": freed_cal}
    
    receivers = [meal_map[k] for k in receiver_keys if k in meal_map]
    
    # 5. Try LLM redistribution
    try:
        receiver_data = []
        for item in receivers:
            nuts = item.nutrients or {}
            p = get_nutrient_val(nuts, ['protein', 'p'])
            c = get_nutrient_val(nuts, ['carbs', 'c'])
            f = get_nutrient_val(nuts, ['fat', 'f'])
            cal = (p * 4) + (c * 4) + (f * 9)
            receiver_data.append({
                "meal_id": item.meal_id,
                "label": item.label,
                "dish_name": item.dish_name,
                "portion_size": item.portion_size,
                "calories": round(cal),
                "protein": round(p, 1),
                "carbs": round(c, 1),
                "fat": round(f, 1),
            })
        
        system_prompt = """You are a nutrition redistribution agent. A user has skipped a meal and the freed calories need to be redistributed to remaining meals.

RULES:
1. PROTEIN BOOST: Use the extra budget to boost protein where possible.
2. BALANCED SPREAD: Don't dump all extra calories into one meal. Spread reasonably.
3. PORTION LOGIC: Increase portions of existing ingredients (e.g., more rice, more chicken).
4. PROVIDE NOTES: Each meal gets a note like "Extra 120 kcal from skipped Snack!"

Respond in JSON:
{
  "redistributed_meals": [
    {
      "meal_id": "dinner",
      "portion_size": "updated portion string",
      "protein": 35.0,
      "carbs": 60.0,
      "fat": 15.0,
      "note": "Extra 120 kcal from skipped Snack! Added 50g rice and 30g chicken."
    }
  ]
}"""

        skipped_label = skipped.label or meal_id.capitalize()
        meals_str = json.dumps(receiver_data, indent=2)
        
        user_prompt = f"""Skipped meal: {skipped_label} ({round(freed_cal)} kcal, P:{freed_p:.0f}g C:{freed_c:.0f}g F:{freed_f:.0f}g)

Remaining meals to receive the extra calories:
{meals_str}

Redistribute the {round(freed_cal)} freed calories across these meals.
Update portion_size, protein, carbs, fat for each meal.
Include a "note" explaining what was added."""

        response = llm_service.call_llm_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=4000
        )
        
        if not response or "redistributed_meals" not in response:
            raise ValueError("LLM returned invalid response")
        
        redistributed = response["redistributed_meals"]
        changes_log = []
        
        for adj in redistributed:
            m_id = adj.get("meal_id", "").lower()
            if m_id not in meal_map:
                continue
            
            item = meal_map[m_id]
            
            new_p = float(adj.get("protein", 0))
            new_c = float(adj.get("carbs", 0))
            new_f = float(adj.get("fat", 0))
            new_cal = (new_p * 4) + (new_c * 4) + (new_f * 9)
            
            new_nuts = dict(item.nutrients or {})
            new_nuts['p'] = round(new_p, 1)
            new_nuts['c'] = round(new_c, 1)
            new_nuts['f'] = round(new_f, 1)
            new_nuts['protein'] = new_nuts['p']
            new_nuts['carbs'] = new_nuts['c']
            new_nuts['fat'] = new_nuts['f']
            new_nuts['calories'] = round(new_cal)
            if 'cal' in new_nuts:
                new_nuts['cal'] = new_nuts['calories']
            
            item.nutrients = new_nuts
            flag_modified(item, "nutrients")
            
            new_portion = adj.get("portion_size", item.portion_size)
            item.portion_size = new_portion
            
            note = adj.get("note", f"Extra {round(freed_cal / len(receivers))} kcal from skipped {skipped_label}!")
            item.feast_notes = [note]
            flag_modified(item, "feast_notes")
            
            changes_log.append(f"{m_id}: +{round(new_cal - receiver_data[0]['calories'])} kcal | {note}")
        
        db.commit()
        
        logger.info(f"[FeastAgent] Skip + Redistribute (LLM): {changes_log}")
        return {
            "message": f"Skipped {skipped_label} and redistributed {round(freed_cal)} kcal",
            "method": "llm",
            "freed_cal": round(freed_cal),
            "changes": changes_log
        }
        
    except Exception as e:
        logger.warning(f"[FeastAgent] LLM redistribution failed ({e}), using even split")
        
        # Fallback: Even split of freed calories
        import re
        per_meal_extra_cal = freed_cal / len(receivers)
        changes_log = []
        
        for item in receivers:
            old_nuts = item.nutrients or {}
            p = get_nutrient_val(old_nuts, ['protein', 'p'])
            c = get_nutrient_val(old_nuts, ['carbs', 'c'])
            f = get_nutrient_val(old_nuts, ['fat', 'f'])
            old_cal = (p * 4) + (c * 4) + (f * 9)
            
            if old_cal > 0:
                ratio = (old_cal + per_meal_extra_cal) / old_cal
            else:
                ratio = 1.0
            
            new_p = round(p * ratio, 1)
            new_c = round(c * ratio, 1)
            new_f = round(f * ratio, 1)
            new_cal = (new_p * 4) + (new_c * 4) + (new_f * 9)
            
            new_nuts = dict(old_nuts)
            new_nuts['p'] = new_p
            new_nuts['c'] = new_c
            new_nuts['f'] = new_f
            new_nuts['protein'] = new_p
            new_nuts['carbs'] = new_c
            new_nuts['fat'] = new_f
            new_nuts['calories'] = round(new_cal)
            if 'cal' in new_nuts:
                new_nuts['cal'] = new_nuts['calories']
            
            item.nutrients = new_nuts
            flag_modified(item, "nutrients")
            
            # Scale portion string
            def scale_portion_string(p_str, factor):
                return re.sub(r'\b(\d+(\.\d+)?)\b', lambda m: f"{float(m.group(1)) * factor:.0f}", p_str)
            
            item.portion_size = scale_portion_string(item.portion_size, ratio)

            skipped_label = skipped.label or meal_id.capitalize()
            note = f"Extra {round(per_meal_extra_cal)} kcal from skipped {skipped_label}!"
            item.feast_notes = [note]
            flag_modified(item, "feast_notes")
            
            changes_log.append(f"{item.meal_id}: {old_cal:.0f} → {new_cal:.0f} kcal | {note}")
        
        db.commit()
        
        logger.info(f"[FeastAgent] Skip + Redistribute (fallback): {changes_log}")
        return {
            "message": f"Skipped {skipped_label} and redistributed {round(freed_cal)} kcal (ratio-based)",
            "method": "fallback",
            "freed_cal": round(freed_cal),
            "changes": changes_log
        }


def restore_original_plan(db: Session, user_id: int):
    """
    Restores the meal plan to the state of the last GENERATION event.
    Reverts all user adjustments (Feast Mode, Single Meal Adjustments, etc.)
    """
    logger.info(f"Restoring original meal plan for user {user_id}")
    
    # 1. Get User Profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        raise ValueError("UserProfile not found")
        
    # 2. Find latest "GENERATION" snapshot
    original_snapshot = db.query(MealPlanHistory)\
        .filter(MealPlanHistory.user_profile_id == profile.id)\
        .filter(MealPlanHistory.change_reason == "GENERATION")\
        .order_by(MealPlanHistory.created_at.desc())\
        .first()
        
    if not original_snapshot:
        return {"error": "No original generated plan found to restore."}
        
    # 3. Validated snapshot content
    if not original_snapshot.meal_plan_snapshot:
        return {"error": "Snapshot exists but content is empty."}
        
    # 4. Clear current plan
    db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).delete()
    
    # 5. Restore from snapshot
    snapshot_data = original_snapshot.meal_plan_snapshot
    new_rows = []
    
    for item in snapshot_data:
        # Convert snapshot dict back to MealPlan object
        # Note: snapshot keys match MealPlan columns
        # However, we must ensure we don't pass extra keys if schema changed
        # Minimal set: meal_id, label, dish_name, portion_size, nutrients, alternatives, guidelines, is_veg
        
        # We explicitly reset is_user_adjusted to False (it should be False in GEN snapshot anyway)
        
        meal = MealPlan(
            user_profile_id=profile.id,
            meal_id=item.get("meal_id"),
            label=item.get("label"),
            dish_name=item.get("dish_name"),
            portion_size=item.get("portion_size"),
            nutrients=item.get("nutrients"),
            alternatives=item.get("alternatives"),
            guidelines=item.get("guidelines"),
            is_veg=item.get("is_veg"),
            is_user_adjusted=False, # Force clean state
            adjustment_note=None,
            feast_notes=None
        )
        new_rows.append(meal)
        
    db.add_all(new_rows)
    db.commit()
    
    # 6. Log this restoration in history?
    # Yes, so we can undo the undo? Or just track it.
    try:
        restore_history = MealPlanHistory(
            user_profile_id=profile.id,
            meal_plan_snapshot=original_snapshot.meal_plan_snapshot, # Same snapshot
            change_reason="RESTORE"
        )
        db.add(restore_history)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log restore history: {e}")
        
    return {"message": "Successfully restored original meal plan."}

