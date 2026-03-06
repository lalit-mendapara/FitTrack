
import httpx
import logging
from typing import Optional, Dict, Any
from app.models.food_item import FoodItem
from config import USDA_API_KEY

logger = logging.getLogger(__name__)

# ============================================================================
# INTELLIGENT CATEGORIZATION FOR USDA API ITEMS
# ============================================================================

# Meal Type Categorization (based on food name keywords)
MEAL_TYPE_KEYWORDS = {
    "breakfast": [
        "cereal", "oats", "oatmeal", "granola", "muesli",
        "toast", "bread", "bagel", "muffin", "pancake", "waffle",
        "egg", "omelet", "omelette",
        "milk", "yogurt", "yoghurt",
        "coffee", "tea",
        "idli", "dosa", "upma", "poha", "paratha"
    ],
    "lunch": [
        "rice", "biryani", "pulao", "khichdi",
        "roti", "chapati", "naan",
        "dal", "curry", "sabzi", "sambar", "rasam",
        "salad", "sandwich", "wrap", "burger",
        "pasta", "noodles",
        "chicken", "fish", "mutton", "paneer"
    ],
    "dinner": [
        "soup", "stew",
        "grilled", "roasted", "baked",
        "kebab", "tikka", "tandoori"
    ],
    "snacks": [
        "fruit", "apple", "banana", "orange", "mango", "grapes",
        "nuts", "almond", "cashew", "walnut", "peanut",
        "chips", "popcorn", "crackers",
        "cookie", "biscuit",
        "samosa", "pakora", "vada",
        "juice", "smoothie", "shake"
    ]
}

# Region Categorization (based on food name keywords)
REGION_KEYWORDS = {
    "North Indian": [
        "paneer", "naan", "paratha", "kulcha", "tandoori",
        "butter chicken", "dal makhani", "rajma", "chole",
        "aloo", "gobi", "palak", "methi"
    ],
    "South Indian": [
        "idli", "dosa", "vada", "upma", "pongal",
        "sambar", "rasam", "coconut", "curry leaf",
        "appam", "uttapam", "medu vada"
    ],
    "Indian": [
        "rice", "dal", "roti", "chapati",
        "curry", "masala", "biryani", "pulao",
        "chutney", "pickle", "raita", "curd", "yogurt"
    ],
    "Asia": [
        "sushi", "ramen", "noodles", "wonton", "dumpling",
        "tofu", "miso", "soy sauce", "teriyaki",
        "kimchi", "pad thai", "pho", "spring roll",
        "fried rice", "chow mein", "tempura"
    ],
    "North America": [
        "burger", "hot dog", "bbq", "ribs", "wings",
        "mac and cheese", "cornbread", "biscuit",
        "pancake", "waffle", "maple syrup",
        "turkey", "pumpkin", "cranberry"
    ],
    "South America": [
        "taco", "burrito", "quesadilla", "enchilada",
        "guacamole", "salsa", "tortilla", "fajita",
        "chimichanga", "empanada", "arepa",
        "black beans", "plantain", "yuca"
    ],
    "Europe": [
        "pasta", "pizza", "risotto", "lasagna",
        "croissant", "baguette", "cheese",
        "steak", "grilled", "roasted", "baked",
        "soup", "stew", "casserole",
        "schnitzel", "bratwurst", "paella"
    ],
    "Africa": [
        "couscous", "tagine", "injera", "berbere",
        "jollof", "fufu", "plantain", "cassava",
        "peri peri", "harissa", "shakshuka"
    ],
    "Australia/Oceania": [
        "vegemite", "lamington", "pavlova",
        "barramundi", "kangaroo", "emu",
        "macadamia", "tim tam"
    ],
    "Western": [
        "bread", "toast", "cereal", "oats", "granola",
        "sandwich", "wrap", "salad",
        "chicken breast", "salmon", "tuna",
        "milk", "egg", "quinoa", "bulgur"
    ]
}

# Default fallbacks
DEFAULT_MEAL_TYPE = "snacks"  # Most generic category
DEFAULT_REGION = "India"      # Your primary market


def categorize_meal_type(food_name: str) -> str:
    """
    Intelligently categorize food into meal type based on name.
    Returns: breakfast, lunch, dinner, or snacks
    """
    name_lower = food_name.lower()
    
    # Score each meal type
    scores = {meal_type: 0 for meal_type in MEAL_TYPE_KEYWORDS.keys()}
    
    for meal_type, keywords in MEAL_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in name_lower:
                scores[meal_type] += 1
    
    # Return meal type with highest score, or default
    max_score = max(scores.values())
    if max_score > 0:
        return max(scores, key=scores.get)
    
    return DEFAULT_MEAL_TYPE


def categorize_region(food_name: str) -> str:
    """
    Intelligently categorize food into region based on name.
    Returns: North Indian, South Indian, Indian, Asia, North America, South America, 
             Europe, Africa, Australia/Oceania, or Western
    """
    name_lower = food_name.lower()
    
    # Check specific regions first (more specific to less specific)
    # Order matters: Check specific regional cuisines before generic ones
    priority_order = [
        "North Indian", "South Indian", "Indian",  # Indian cuisines first
        "Asia", "North America", "South America",  # Continental regions
        "Europe", "Africa", "Australia/Oceania",   # Other regions
        "Western"  # Generic Western last
    ]
    
    for region in priority_order:
        keywords = REGION_KEYWORDS[region]
        for keyword in keywords:
            if keyword in name_lower:
                return region
    
    return DEFAULT_REGION


class FoodAPIService:
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"

    def __init__(self):
        self.api_key = USDA_API_KEY
        if not self.api_key:
            logger.warning("USDA_API_KEY not set. Food API service will not work.")

    def search_food(self, query: str, limit: int = 3) -> Optional[Dict[str, Any]]:
        """
        Search for a food item in USDA database (Synchronous).
        Returns the best match details or None.
        """
        if not self.api_key:
            return None

        # Clean query
        query = query.replace("(veg)", "").replace("(non-veg)", "").strip()

        # Prioritize "Foundation" and "SR Legacy" data types
        params = {
            "api_key": self.api_key,
            "query": query,
            "pageSize": limit,
            "dataType": ["Foundation", "SR Legacy"]
        }

        try:
            with httpx.Client() as client:
                response = client.get(f"{self.BASE_URL}/foods/search", params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()

                if not data.get("foods"):
                    # Retry without dataType filter if no results
                    params.pop("dataType")
                    response = client.get(f"{self.BASE_URL}/foods/search", params=params, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
                
                if data.get("foods"):
                    return data["foods"][0] # Return top match
                
                return None

        except Exception as e:
            logger.error(f"Error searching USDA API for '{query}': {e}")
            return None

    def _extract_nutrient(self, food_data: Dict, nutrient_ids: list) -> float:
        """Helper to extract nutrient value from food nutrients list."""
        nutrients = food_data.get("foodNutrients", [])
        for n in nutrients:
            if n.get("nutrientId") in nutrient_ids:
                return float(n.get("value", 0))
        return 0.0

    def get_food_item(self, query: str, diet_type: str = "veg", meal_type: str = None) -> Optional[FoodItem]:
        """
        Search and convert to local FoodItem model (Synchronous).
        Automatically categorizes meal_type and region based on food name.
        """
        match = self.search_food(query)
        if not match:
            return None

        # Extract values
        protein = self._extract_nutrient(match, [1003, 203]) # Protein
        fat = self._extract_nutrient(match, [1004, 204])    # Fat
        carbs = self._extract_nutrient(match, [1005, 205])  # Carbs
        calories = self._extract_nutrient(match, [1008, 208]) # Energy (kcal)

        # If calories missing but macros present, calculate
        if calories == 0 and (protein > 0 or fat > 0 or carbs > 0):
            calories = (protein * 4) + (carbs * 4) + (fat * 9)

        # Get food name from USDA
        food_name = match.get("description")
        
        # Intelligent categorization
        auto_meal_type = categorize_meal_type(food_name)
        auto_region = categorize_region(food_name)
        
        # Use provided meal_type if valid, otherwise use auto-categorized
        final_meal_type = meal_type if meal_type in ["breakfast", "lunch", "dinner", "snacks"] else auto_meal_type

        food_item = FoodItem(
            fdc_id=str(match.get("fdcId")),
            name=food_name,
            diet_type=diet_type, 
            meal_type=final_meal_type,  # Auto-categorized or provided
            serving_size_g=100.0, 
            protein_g=protein,
            fat_g=fat,
            carb_g=carbs,
            calories_kcal=calories,
            region=auto_region,  # Auto-categorized based on food name
            vector_text=f"{food_name} usda {auto_region.lower()}"
        )
        
        logger.info(f"[USDA-API] Found: {food_item.name} | Meal: {final_meal_type} | Region: {auto_region} | {food_item.calories_kcal}kcal/100g")
        return food_item

food_api_service = FoodAPIService()
