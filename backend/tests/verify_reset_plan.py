import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.database import SessionLocal
from app.services.meal_service import generate_meal_plan, adjust_single_meal, restore_original_plan
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.meal_plan import MealPlan
from app.models.meal_plan_history import MealPlanHistory

async def test_reset_flow():
    db = SessionLocal()
    try:
        # 1. Setup - Get User
        print("\n--- SETUP: GET USER ---")
        user = db.query(UserProfile).join(User).filter(User.gender.in_(['male', 'female', 'Male', 'Female'])).first()
        if not user:
            print("No user found! Please generate a profile first.")
            return

        user_id = user.user_id
        profile_id = user.id
        print(f"Testing with User ID: {user_id} (Profile ID: {profile_id})")
        
        # 2. Generate Initial Plan (Snapshot: GENERATION)
        print("\n--- TEST: GENERATE PLAN ---")
        print("Generating new plan to establish baseline...")
        generate_meal_plan(db, user_id, custom_prompt="Test reset plan")
        
        # Verify GENERATION snapshot
        gen_snapshot = db.query(MealPlanHistory)\
            .filter(MealPlanHistory.user_profile_id == profile_id)\
            .filter(MealPlanHistory.change_reason == "GENERATION")\
            .order_by(MealPlanHistory.created_at.desc())\
            .first()
            
        if not gen_snapshot:
            print("❌ Failed to create GENERATION snapshot during generation!")
            return
        print("✅ GENERATION snapshot created.")
        
        # Capture baseline properties of a meal (e.g. Lunch)
        original_lunch = db.query(MealPlan).filter(
            MealPlan.user_profile_id == profile_id,
            MealPlan.label.ilike("lunch")
        ).first()
        
        print(f"Original Lunch: {original_lunch.dish_name} ({original_lunch.portion_size})")
        original_details = {
            "dish": original_lunch.dish_name,
            "cal": original_lunch.nutrients.get('calories')
        }
        
        # 3. Adjust a Meal (Snapshot: USER_ADJUSTMENT)
        print("\n--- TEST: ADJUST MEAL (Simulate User Edit) ---")
        # Adjust Lunch to be "Pizza"
        override = {
            "food_items": ["Pizza"],
            "total_calories": 800,
            "note": "Cheat meal"
        }
        
        adjust_result = adjust_single_meal(db, user_id, "lunch", override_info=override)
        if "error" in adjust_result:
            print(f"❌ Adjustment failed: {adjust_result}")
            return
            
        print("✅ Lunch adjusted to Pizza.")
        
        # Verify USER_ADJUSTMENT snapshot
        adj_snapshot = db.query(MealPlanHistory)\
            .filter(MealPlanHistory.user_profile_id == profile_id)\
            .filter(MealPlanHistory.change_reason == "USER_ADJUSTMENT")\
            .order_by(MealPlanHistory.created_at.desc())\
            .first()
            
        if not adj_snapshot:
            print("❌ Failed to create USER_ADJUSTMENT snapshot!")
            # Proceeding anyway to test reset, but this is a failure
        else:
            print("✅ USER_ADJUSTMENT snapshot created.")
            
        # Verify DB is updated
        adjusted_lunch = db.query(MealPlan).filter(
            MealPlan.user_profile_id == profile_id,
            MealPlan.label.ilike("lunch")
        ).first()
        
        if not adjusted_lunch.is_user_adjusted:
             print("❌ Meal not marked as user adjusted in DB!")
             
        print(f"Adjusted Lunch: {adjusted_lunch.dish_name} (User Adjusted: {adjusted_lunch.is_user_adjusted})")
        
        # 4. RESET PLAN (Restore GENERATION snapshot)
        print("\n--- TEST: RESET PLAN ---")
        reset_result = restore_original_plan(db, user_id)
        print(f"Reset Result: {reset_result}")
        
        if "error" in reset_result:
            print("❌ Reset failed!")
            return
            
        # 5. VERIFY RESTORATION
        print("\n--- VERIFICATION ---")
        restored_lunch = db.query(MealPlan).filter(
            MealPlan.user_profile_id == profile_id,
            MealPlan.label.ilike("lunch")
        ).first()
        
        print(f"Restored Lunch: {restored_lunch.dish_name} (User Adjusted: {restored_lunch.is_user_adjusted})")
        
        # Checks
        checks_passed = True
        
        # Check 1: Dish Name matches original
        if restored_lunch.dish_name != original_details["dish"]:
            print(f"❌ Dish name mismatch! Expected '{original_details['dish']}', got '{restored_lunch.dish_name}'")
            checks_passed = False
            
        # Check 2: is_user_adjusted is False
        if restored_lunch.is_user_adjusted:
            print("❌ Restored meal is still marked as user adjusted!")
            checks_passed = False
            
        # Check 3: Check history for RESTORE event
        restore_snapshot = db.query(MealPlanHistory)\
            .filter(MealPlanHistory.user_profile_id == profile_id)\
            .filter(MealPlanHistory.change_reason == "RESTORE")\
            .order_by(MealPlanHistory.created_at.desc())\
            .first()
            
        if restore_snapshot:
             print("✅ RESTORE event logged in history.")
        else:
             print("⚠️ No RESTORE event found in history (Optional but recommended).")
             
        if checks_passed:
            print("\n🎉 SUCCESS: Plan successfully reset to original state!")
        else:
            print("\n❌ FAILURE: Restoration verification failed.")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_reset_flow())
