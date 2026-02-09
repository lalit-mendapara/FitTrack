
import httpx
import logging
from typing import Optional, Dict, Any
from app.models.food_item import FoodItem
from config import USDA_API_KEY

logger = logging.getLogger(__name__)

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

    def get_food_item(self, query: str, diet_type: str = "veg", meal_type: str = "balanced") -> Optional[FoodItem]:
        """
        Search and convert to local FoodItem model (Synchronous).
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

        food_item = FoodItem(
            fdc_id=str(match.get("fdcId")),
            name=match.get("description"),
            diet_type=diet_type, 
            meal_type=meal_type,
            serving_size_g=100.0, 
            protein_g=protein,
            fat_g=fat,
            carb_g=carbs,
            calories_kcal=calories,
            region="USDA-API", # Source Logging
            vector_text=f"{match.get('description')} usda"
        )
        
        logger.info(f"[USDA-API] Found: {food_item.name} ({food_item.calories_kcal}kcal/100g)")
        return food_item

food_api_service = FoodAPIService()
