"""
Ingredient Mapper Module
-------------------------
Maps LLM-generated dish names to FoodItem database records.
This module is the bridge between LLM's creative dish selection and DB-based nutrient calculation.

Flow:
1. LLM outputs: "Poha (veg) + Curd + Apple"
2. This module: Parses -> ["Poha", "Curd", "Apple"] -> [FoodItem, FoodItem, FoodItem]
3. Optimizer uses: FoodItem macros to calculate portions
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.food_item import FoodItem

logger = logging.getLogger(__name__)

# ============================================================================
# TERMINAL LOGGING UTILITIES
# ============================================================================

def log_ingredient_mapping_start(dish_name: str, meal_id: str):
    """Log the start of ingredient mapping process."""
    print("\n" + "─" * 70)
    print(f"  🍽️  INGREDIENT MAPPER: Processing {meal_id.upper()}")
    print("─" * 70)
    print(f"  Input Dish: {dish_name}")
    print("")


def log_ingredient_match(ingredient: str, food_item: Optional[FoodItem], match_type: str):
    """Log individual ingredient match results."""
    if food_item:
        print(f"  ✓ {ingredient:25} → {food_item.name:25} [{match_type}]")
        print(f"    └── Per 100g: P={float(food_item.protein_g):.1f}g, C={float(food_item.carb_g):.1f}g, F={float(food_item.fat_g):.1f}g, Cal={float(food_item.calories_kcal):.0f}")
    else:
        print(f"  ✗ {ingredient:25} → NOT FOUND (will use fallback)")


def log_ingredient_mapping_summary(found: int, total: int, meal_id: str):
    """Log summary of ingredient mapping."""
    success_rate = (found / total * 100) if total > 0 else 0
    status = "✓" if success_rate >= 80 else "⚠"
    print("")
    print(f"  {status} Summary: {found}/{total} ingredients mapped ({success_rate:.0f}%)")
    print("─" * 70 + "\n")


# ============================================================================
# PARSING FUNCTIONS
# ============================================================================

def extract_ingredients_from_dish(dish_name: str) -> List[str]:
    """
    Parses a composite dish name into individual ingredient names.
    
    Examples:
        "Poha (veg) + Curd + Apple" -> ["Poha", "Curd", "Apple"]
        "Chicken Curry (non-veg) + Rice + Salad" -> ["Chicken Curry", "Rice", "Salad"]
        "2 Roti + Dal Tadka" -> ["Roti", "Dal Tadka"]
    
    Returns:
        List of cleaned ingredient names
    """
    if not dish_name:
        return []
    
    # Step 1: Remove veg/non-veg labels
    cleaned = re.sub(r'\s*\((?:non-)?veg\)\s*', ' ', dish_name, flags=re.IGNORECASE)
    
    # Step 2: Split by common delimiters: +, with, and, &
    parts = re.split(r'\s*[+&]\s*|\s+with\s+|\s+and\s+', cleaned, flags=re.IGNORECASE)
    
    # Step 3: Clean each part
    ingredients = []
    for part in parts:
        # Remove leading numbers and units (e.g., "2 Roti" -> "Roti", "150g Rice" -> "Rice")
        cleaned_part = re.sub(r'^\d+\s*(g|ml|gm|grams?)?\s*', '', part.strip(), flags=re.IGNORECASE)
        cleaned_part = cleaned_part.strip()
        
        if cleaned_part and len(cleaned_part) > 1:
            ingredients.append(cleaned_part)
    
    return ingredients


def _clean_ingredient_name_for_search(name: str) -> str:
    """
    Prepares ingredient name for database search.
    Removes common prefixes/suffixes that might hinder matching.
    """
    # Remove common descriptors that aren't in DB
    descriptors = ['steamed', 'grilled', 'fried', 'boiled', 'roasted', 'baked', 
                   'fresh', 'plain', 'mixed', 'homemade', 'sliced', 'chopped']
    
    name_lower = name.lower()
    for desc in descriptors:
        name_lower = re.sub(rf'\b{desc}\b\s*', '', name_lower)
    
    return name_lower.strip()


# ============================================================================
# DATABASE MAPPING FUNCTIONS
# ============================================================================

def find_food_item_exact(db: Session, name: str, diet_type: str = None) -> Optional[FoodItem]:
    """
    Attempts exact case-insensitive match in FoodItem table.
    """
    query = db.query(FoodItem).filter(func.lower(FoodItem.name) == name.lower())
    
    if diet_type and diet_type.lower() in ['veg', 'vegetarian']:
        query = query.filter(FoodItem.diet_type == 'veg')
    
    return query.first()


def find_food_item_partial(db: Session, name: str, diet_type: str = None) -> Optional[FoodItem]:
    """
    Attempts partial match using ILIKE with word boundary awareness.
    Avoids false positives like "apple" matching "pineapple".
    """
    # Clean name for search
    search_name = _clean_ingredient_name_for_search(name)
    
    # Try word-boundary aware search
    query = db.query(FoodItem).filter(
        FoodItem.name.ilike(f"%{search_name}%")
    )
    
    if diet_type and diet_type.lower() in ['veg', 'vegetarian']:
        query = query.filter(FoodItem.diet_type == 'veg')
    
    results = query.limit(5).all()
    
    # Score results by relevance
    best_match = None
    best_score = 0
    
    for item in results:
        item_lower = item.name.lower()
        search_lower = search_name.lower()
        
        # Exact match gets highest score
        if item_lower == search_lower:
            return item
        
        # Word boundary match (e.g., "apple" in "green apple" but not in "pineapple")
        if re.search(rf'\b{re.escape(search_lower)}\b', item_lower):
            score = len(search_lower) / len(item_lower)  # Prefer shorter DB names
            if score > best_score:
                best_score = score
                best_match = item
    
    return best_match


def find_food_item_fuzzy(db: Session, name: str, diet_type: str = None) -> Optional[FoodItem]:
    """
    Uses VectorService for semantic similarity search.
    Fallback when exact/partial matches fail.
    """
    try:
        from app.services.vector_service import VectorService
        vector_service = VectorService()
        
        if not vector_service.client:
            return None
        
        results = vector_service.search_food(name, limit=3, threshold=0.4)
        
        if results:
            # Get top result and look it up in DB
            top_result = results[0]
            food_name = top_result.get('name') or top_result.get('food_name')
            
            if food_name:
                return find_food_item_exact(db, food_name, diet_type)
    
    except Exception as e:
        logger.warning(f"[IngredientMapper] Vector search failed for '{name}': {e}")
    
    return None


def map_ingredients_to_food_items(
    db: Session, 
    ingredients: List[str], 
    diet_type: str = None,
    meal_id: str = "meal"
) -> List[Tuple[str, Optional[FoodItem], str]]:
    """
    Maps a list of ingredient names to FoodItem database records.
    
    Strategy (in order):
    1. Exact match (fastest, most accurate)
    2. Partial match with word boundary
    3. Fuzzy/semantic match via VectorService
    
    Args:
        db: Database session
        ingredients: List of ingredient names from LLM
        diet_type: User's diet preference (veg/non-veg)
        meal_id: For logging purposes
    
    Returns:
        List of tuples: (ingredient_name, FoodItem or None, match_type)
    """
    results = []
    found_count = 0
    
    for ingredient in ingredients:
        food_item = None
        match_type = "NOT_FOUND"
        
        # Strategy 1: Exact match
        food_item = find_food_item_exact(db, ingredient, diet_type)
        if food_item:
            match_type = "EXACT"
            found_count += 1
        
        # Strategy 2: Partial match
        if not food_item:
            food_item = find_food_item_partial(db, ingredient, diet_type)
            if food_item:
                match_type = "PARTIAL"
                found_count += 1
        
        # Strategy 3: Fuzzy/Vector match
        if not food_item:
            food_item = find_food_item_fuzzy(db, ingredient, diet_type)
            if food_item:
                match_type = "FUZZY"
                found_count += 1
        
        # Log individual match
        log_ingredient_match(ingredient, food_item, match_type)
        
        results.append((ingredient, food_item, match_type))
    
    # Log summary
    log_ingredient_mapping_summary(found_count, len(ingredients), meal_id)
    
    return results


def map_dish_to_food_items(
    db: Session,
    dish_name: str,
    diet_type: str = None,
    meal_id: str = "meal"
) -> List[Tuple[str, Optional[FoodItem], str]]:
    """
    Convenience function: Parses dish name and maps to food items in one call.
    
    Args:
        db: Database session
        dish_name: Full dish name from LLM (e.g., "Poha (veg) + Curd + Apple")
        diet_type: User's diet preference
        meal_id: For logging
    
    Returns:
        List of tuples: (ingredient_name, FoodItem or None, match_type)
    """
    # Log start
    log_ingredient_mapping_start(dish_name, meal_id)
    
    # Parse ingredients
    ingredients = extract_ingredients_from_dish(dish_name)
    
    if not ingredients:
        logger.warning(f"[IngredientMapper] No ingredients parsed from: {dish_name}")
        print(f"  ⚠ No ingredients could be parsed from dish name")
        print("─" * 70 + "\n")
        return []
    
    print(f"  Parsed Ingredients: {ingredients}")
    print("")
    
    # Map to food items
    return map_ingredients_to_food_items(db, ingredients, diet_type, meal_id)


# ============================================================================
# FALLBACK MACROS (When DB lookup fails)
# ============================================================================

# These are per-100g estimates for common ingredients not in the database
FALLBACK_MACROS = {
    "rice": {"p": 2.7, "c": 28.0, "f": 0.3, "cal": 130},
    "roti": {"p": 8.0, "c": 50.0, "f": 3.0, "cal": 264},
    "chapati": {"p": 8.0, "c": 50.0, "f": 3.0, "cal": 264},
    "dal": {"p": 9.0, "c": 20.0, "f": 0.5, "cal": 104},
    "salad": {"p": 1.0, "c": 4.0, "f": 0.2, "cal": 20},
    "curd": {"p": 3.5, "c": 4.5, "f": 3.0, "cal": 60},
    "yogurt": {"p": 3.5, "c": 4.5, "f": 3.0, "cal": 60},
    "egg": {"p": 13.0, "c": 1.1, "f": 11.0, "cal": 155},
    "chicken": {"p": 27.0, "c": 0.0, "f": 3.6, "cal": 165},
    "paneer": {"p": 18.0, "c": 1.2, "f": 21.0, "cal": 265},
    "milk": {"p": 3.3, "c": 4.8, "f": 3.3, "cal": 61},
    "apple": {"p": 0.3, "c": 14.0, "f": 0.2, "cal": 52},
    "banana": {"p": 1.1, "c": 23.0, "f": 0.3, "cal": 89},
}


def get_fallback_macros(ingredient_name: str) -> Dict[str, float]:
    """
    Returns per-100g macros for an ingredient when DB lookup fails.
    Uses fuzzy matching against fallback dictionary.
    """
    name_lower = ingredient_name.lower()
    
    # Direct match
    if name_lower in FALLBACK_MACROS:
        return FALLBACK_MACROS[name_lower]
    
    # Partial match
    for key, macros in FALLBACK_MACROS.items():
        if key in name_lower or name_lower in key:
            return macros
    
    # Default fallback (balanced macro estimate)
    return {"p": 5.0, "c": 15.0, "f": 5.0, "cal": 125}
