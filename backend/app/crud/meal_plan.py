
from sqlalchemy.orm import Session
from app.models.meal_plan import MealPlan
from app.models.user_profile import UserProfile
from app.schemas.meal_plan import MealPlanResponse, MealItem, NutrientDetail, NutrientTotals

"""
Meal Plan CRUD
--------------
Pure Database Access Object for Meal Plans.
Business logic for generation has been moved to app.services.meal_service.
"""

def get_current_meal_plan(db: Session, user_id: int):
    """
    Retrieve the existing meal plan for a user.
    """
    try:
        # 1. Get User Profile
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            return None
        
        # 2. Get Meal Plan Items
        meal_items = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()
        
        if not meal_items:
            return None
            
        # 3. Convert to Response Items
        response_items = []
        for m in meal_items:
             # Ensure lists
            guidelines = m.guidelines or []
            if isinstance(guidelines, str):
                guidelines = [guidelines]
            
            alternatives = m.alternatives or []
            if isinstance(alternatives, str):
                alternatives = [alternatives]

            response_items.append(MealItem(
                meal_id=m.meal_id,
                label=m.label,
                is_veg=m.is_veg,
                dish_name=m.dish_name,
                portion_size=m.portion_size,
                nutrients=NutrientDetail(
                    p=float(m.nutrients.get('p', m.nutrients.get('protein', 0))),
                    c=float(m.nutrients.get('c', m.nutrients.get('carbs', 0))),
                    f=float(m.nutrients.get('f', m.nutrients.get('fat', 0)))
                ),
                alternatives=alternatives,
                guidelines=guidelines,
                feast_notes=m.feast_notes or [],
            ))
            
        # 4. Calculate Totals (on the fly to be accurate to what's stored)
        total_protein = sum(item.nutrients.p for item in response_items)
        total_carbs = sum(item.nutrients.c for item in response_items)
        total_fat = sum(item.nutrients.f for item in response_items)
        total_calories = (total_protein * 4) + (total_carbs * 4) + (total_fat * 9)
        
        return MealPlanResponse(
            user_profile_id=profile.id,
            daily_targets=NutrientTotals(
                calories=profile.calories,
                protein=profile.protein,
                carbs=profile.carbs,
                fat=profile.fat
            ),
            daily_generated_totals=NutrientTotals(
                calories=total_calories,
                protein=total_protein,
                carbs=total_carbs,
                fat=total_fat
            ),
            meal_plan=response_items,
            verification=f"Retrieved {len(response_items)} meals from database",
            created_at=meal_items[0].created_at if meal_items else None
        )
        
    except Exception as e:
        print(f"Error fetching current meal plan: {e}")
        return None

def get_meal_plan(db: Session, user_id: int):
    """
    Retrieve the raw existing meal plan DB OBJECTS for a user.
    Used for Smart Merge restoration.
    """
    try:
        # 1. Get User Profile
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            return None
        
        # 2. Get Meal Plan Items
        meal_items = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()
        
        return meal_items
        
    except Exception as e:
        print(f"Error fetching raw meal plan: {e}")
        return None