
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
                is_user_adjusted=m.is_user_adjusted or False,
                adjustment_note=m.adjustment_note,
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

def update_single_meal(db: Session, user_profile_id: int, meal_id: str, updated_fields: dict) -> MealPlan:
    """
    Update a single meal in the plan for a specific profile.
    
    Args:
        db: Database session
        user_profile_id: The ID of the user profile (not user_id)
        meal_id: The meal identifier (e.g., 'breakfast')
        updated_fields: Dictionary of fields to update
        
    Returns:
        The updated MealPlan object or None if not found.
    """
    try:
        # Find the specific meal
        meal = db.query(MealPlan).filter(
            MealPlan.user_profile_id == user_profile_id,
            MealPlan.meal_id == meal_id
        ).first()
        
        if not meal:
            return None
            
        # Update fields
        for key, value in updated_fields.items():
            if hasattr(meal, key):
                setattr(meal, key, value)
        
        # Explicitly flag JSON fields as modified if they are updated
        # This ensures SQLAlchemy detects changes inside JSON objects
        from sqlalchemy.orm.attributes import flag_modified
        if 'nutrients' in updated_fields:
            flag_modified(meal, 'nutrients')
        if 'alternatives' in updated_fields:
            flag_modified(meal, 'alternatives')
        if 'guidelines' in updated_fields:
            flag_modified(meal, 'guidelines')
        if 'feast_notes' in updated_fields:
            flag_modified(meal, 'feast_notes')
            
        db.commit()
        db.refresh(meal)
        return meal
        
    except Exception as e:
        db.rollback()
        return None

def get_current_meal_plan_with_overrides(db: Session, user_id: int):
    """
    Returns meal plan with feast overrides merged in. Original values preserved.
    """
    from datetime import date
    base_plan = get_current_meal_plan(db, user_id)
    if not base_plan or not base_plan.meal_plan:
        return base_plan
        
    try:
        from app.services.feast_mode_manager import FeastModeManager
        manager = FeastModeManager(db)
        overrides = manager.get_overrides_for_date(user_id, date.today())
        
        if not overrides:
            return base_plan
            
        # Apply Overrides
        updated_items = []
        total_p = total_c = total_f = total_cal = 0.0
        
        for item in base_plan.meal_plan:
            # Check for override
            override = overrides.get(item.meal_id.lower())
            
            if override:
                # Store original values
                item.original_nutrients = item.nutrients
                item.original_portion_size = item.portion_size
                
                # Apply new values
                item.nutrients = NutrientDetail(
                    p=override.adjusted_protein,
                    c=override.adjusted_carbs,
                    f=override.adjusted_fat,
                )
                item.portion_size = override.adjusted_portion_size
                item.feast_notes = [override.adjustment_note] if override.adjustment_note else []
                # item.is_user_adjusted = True # Maybe? Or keep separate flag
            
            updated_items.append(item)
            
            # Recalculate totals
            total_p += item.nutrients.p
            total_c += item.nutrients.c
            total_f += item.nutrients.f
            
        total_cal = (total_p * 4) + (total_c * 4) + (total_f * 9)
        
        # Update Generated Totals in Response
        base_plan.daily_generated_totals = NutrientTotals(
            calories=total_cal,
            protein=total_p,
            carbs=total_c,
            fat=total_f
        )
        base_plan.meal_plan = updated_items
        base_plan.verification += f" (Merged {len(overrides)} Overrides)"
        
        return base_plan
        
    except Exception as e:
        print(f"Error applying overrides: {e}")
        return base_plan # Return base plan if merge fails