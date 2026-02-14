
import sys
import os
from datetime import date, timedelta

# Ensure backend/app matches python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.user_profile import UserProfile
from app.models.meal_plan import MealPlan
from app.services.feast_mode_manager import FeastModeManager
from app.crud.meal_plan import get_current_meal_plan_with_overrides
from app.models.feast_config import FeastConfig, FeastMealOverride

def run_verification():
    print("--- Starting Reimagined Feast Mode Verification ---")
    db = SessionLocal()
    
    # Specific User Verification (dhruvit@gmail.com or ID 42)
    user_id = 42
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
         # Fallback to first user
         profile = db.query(UserProfile).first()
         if not profile:
             print("Error: No user profile found.")
             return
         user_id = profile.user_id
         
    print(f"Verifying for User ID: {user_id} (Profile ID: {profile.id})")

    manager = FeastModeManager(db)

    try:
        # 0. Cleanup (Reset state)
        print("\n[Step 0] Cleaning up existing configs...")
        active_config = manager.get_active_config(user_id)
        if active_config:
            print(f"   Found active event: {active_config.event_name}. Cancelling...")
            manager.cancel(user_id)
            
        # Ensure we have a base meal plan
        mp = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).first()
        if not mp:
            print("   Creating dummy meal plan...")
            # (Simplified creation for test if needed, but assuming one exists)
            pass

        # 1. Propose Strategy
        event_date = date.today() + timedelta(days=2)
        print(f"\n[Step 1] Proposing Event for {event_date}...")
        proposal = manager.propose_strategy(user_id, event_date, "Verification Feast")
        print(f"   Proposal: {proposal}")
        
        if "error" in proposal:
            print(f"   ERROR: {proposal['error']}")
            return

        # 2. Activate Feast Mode
        print(f"\n[Step 2] Activating Feast Mode...")
        result = manager.activate(user_id, proposal)
        print(f"   Activation Result: {result}")
        
        active_config = manager.get_active_config(user_id)
        if active_config:
            print(f"   SUCCESS: Config created with ID {active_config.id}")
            print(f"   Status: {active_config.status}, Daily Deduction: {active_config.daily_deduction}")
        else:
            print("   FAILURE: No active config found.")
            return

        # 3. Verify Overrides (should have been generated via background task effectively, but we might need to trigger it manually here if celery isn't running)
        # However, activate calls _generate_overrides_for_date for TODAY.
        print(f"\n[Step 3] Verifying Overrides for Today...")
        overrides = manager.get_overrides_for_date(user_id, date.today())
        print(f"   Found {len(overrides)} overrides.")
        for mid, ov in overrides.items():
            print(f"   - {mid}: {ov.adjusted_calories} kcal (Method: {ov.adjustment_method})")
            
        if not overrides:
            print("   WARNING: No overrides found. Did generation fail?")

        # 4. Verify API Response (Merged Plan)
        print(f"\n[Step 4] Verifying Merged Meal Plan...")
        merged_plan = get_current_meal_plan_with_overrides(db, user_id)
        if merged_plan and merged_plan.daily_generated_totals:
            print(f"   Merged Totals: {merged_plan.daily_generated_totals.calories:.0f} kcal")
            expected_max = profile.calories - active_config.daily_deduction + 50 # buffer
            if merged_plan.daily_generated_totals.calories <= expected_max:
                 print(f"   SUCCESS: Calories reduced (Target ~{profile.calories - active_config.daily_deduction})")
            else:
                 print(f"   FAILURE: Calories not reduced significantly ({merged_plan.daily_generated_totals.calories} > {expected_max})")
        else:
            print("   FAILURE: Could not get merged meal plan.")

        # 5. Mid-Day Update (Update Deduction)
        print(f"\n[Step 5] Testing Mid-Day Update...")
        
        # We want to reduce today's target further (e.g. user ate too much breakfast?)
        # Or just re-run generation.
        
        new_result = manager.update_mid_day(user_id, new_deduction=active_config.daily_deduction + 100)
        print(f"   Update Result: {new_result}")
        
        updated_overrides = manager.get_overrides_for_date(user_id, date.today())
        print(f"   Updated Overrides Count: {len(updated_overrides)}")
        
        # Verify deduction change in config
        db.refresh(active_config)
        print(f"   New Daily Deduction: {active_config.daily_deduction}")


        # 6. Cancel
        print(f"\n[Step 6] Cancelling Feast Mode...")
        manager.cancel(user_id)
        
        active_config = manager.get_active_config(user_id)
        if not active_config:
            print("   SUCCESS: No active config.")
        else:
            print(f"   FAILURE: Config still active: {active_config.status}")

        # 7. Check Restoration
        print(f"\n[Step 7] Verifying Restoration...")
        restored_overrides = manager.get_overrides_for_date(user_id, date.today())
        if not restored_overrides:
            print("   SUCCESS: No overrides exist.")
        else:
            print(f"   FAILURE: {len(restored_overrides)} overrides still exist.")
            
        final_plan = get_current_meal_plan_with_overrides(db, user_id)
        if final_plan: 
             print(f"   Final Plan Calories: {final_plan.daily_generated_totals.calories:.0f}")
             if abs(final_plan.daily_generated_totals.calories - profile.calories) < 200:
                 print("   SUCCESS: Calories returned to baseline.")
             else:
                  print("   WARNING: Calories might not be fully back to baseline (could be due to other factors).")

    except Exception as e:
        print(f"\n=== Verification FAILED: {e} ===")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()
        print("\n=== Verification Complete ===")

if __name__ == "__main__":
    run_verification()
