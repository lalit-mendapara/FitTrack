
import sys
import os
# Ensure backend/app matches python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.meal_plan import MealPlan
from app.services import social_event_service, workout_service, meal_service
from app.crud.meal_plan import get_current_meal_plan
from datetime import date, timedelta

def run_verification():
    print("--- Starting Feast Feature Verification ---")
    db = SessionLocal()
    
    # Dynamic User Selection: Get first user with a profile
    # profile = db.query(UserProfile).first()
    # if not profile:
    #     print("ERROR: No UserProfile found in DB. Cannot run verification.")
    #     return
        
    # user_id = profile.user_id
    
    # Specific User Verification (dhruvit@gmail.com)
    user_id = 42
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
         print(f"Error: User {user_id} has no profile.")
         return
         
    print(f"Verifying for User ID: {user_id} (Profile ID: {profile.id})")

    try:
        # 0. Cleanup (Reset state)
        active = social_event_service.get_active_event(db, user_id)
        if active and active.is_active:
            print(f"[Cleanup] Found existing active event: {active.event_name}. Cancelling to start fresh...")
            social_event_service.cancel_active_event(db, user_id)
            # Also restore workout if needed
            workout_service.restore_workout_plan(db, user_id, active.event_date)
            
        # 1. Create Dummy Meal Plan for user if not exists (BEFORE CONFIRMING EVENT)
        # Check if exists first
        existing_mp = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).first()
        if not existing_mp:
            print("[Setup] Creating dummy meal plan (2000 kcal)...")
            mp_item = MealPlan(
                user_profile_id=profile.id,
                meal_id="lunch",
                label="Lunch",
                is_veg=True,
                dish_name="Test Dish",
                portion_size="400g Rice",
                nutrients={"calories": 3200, "protein": 150, "carbs": 500, "fat": 80}
            )
            db.add(mp_item)
            db.commit()
        else:
             print("[Setup] Found existing meal plan.")

        # 2. Create Proposal (for 2 days from now)
        event_date = date.today() + timedelta(days=2)
        print(f"\n[Step 1] Proposing Event for {event_date}...")
        proposal = social_event_service.propose_banking_strategy(db, user_id, event_date, "Verification Party")
        print(f"   Proposal: {proposal}")
        
        # 3. Confirm Event (Banking Phase)
        print(f"\n[Step 2] Confirming Event (Start Banking)...")
        if "error" not in proposal:
            event = social_event_service.create_social_event(db, user_id, proposal)
            print(f"   Event Created: ID {event.id}")
            
            # Manually trigger adjustment because confirm_event logic in script might be different from API
            print(f"   [Simulation] Triggering meal plan adjustment...")
            # We assume a daily deduction of ~400 kcal
            deduction = proposal.get("daily_deduction", 400)
            target = max(1200, profile.calories - deduction)
            print(f"   Adjustment Target: {target} kcal (Base: {profile.calories} - {deduction})")
            
            meal_service.adjust_todays_meal_plan(db, user_id, target, []) 

            # 4. Patch Workout (Simulate API call)
            today = date(2026, 2, 11)
            print("[Step 3] Patching Workout (Glycogen Depletion)...")
            workout_service.patch_limit_day_workout(db, user_id, today)
            print("   Workout Patched.")
            
            # --- VERIFY MEAL PLAN ADJUSTMENT ---
            db.expire_all() # Force reload from DB to see committed changes
            mp = get_current_meal_plan(db, user_id)
            if mp:
                 print(f"   [MEAL CHECK] New Totals: {mp.daily_generated_totals.calories:.0f} kcal")
                 
                 if mp.daily_generated_totals.calories < 2000: # Expected drop below base
                      print("   SUCCESS: Meal plan calories reduced!")
                 else:
                      print("   FAILURE: Meal plan calories did NOT drop significantly.")
            else:
                print("   [MEAL CHECK] No meal plan found to verify adjustment.")
            # -----------------------------------
            
            # 5. Verify Active State
            print(f"[Step 4] Verifying Active State...")
            active = social_event_service.get_active_event(db, user_id)
            if active and active.is_active and active.event_name == "Verification Party":
                 print("   SUCCESS: Event is active.")
            else:
                 print("   FAILED: Event not active.")
                 
            # 6. Cancel Event (Undo)
            print(f"[Step 5] Cancelling Event (Undo)...")
            cancel_result = social_event_service.cancel_active_event(db, user_id)
            print(f"   Cancel Result: {cancel_result}")
            
            # Verify Restoration
            mp_restored = get_current_meal_plan(db, user_id)
            if mp_restored:
                 print(f"   [MEAL CHECK] Restored Totals: {mp_restored.daily_generated_totals.calories:.0f} kcal")
                 if mp_restored.daily_generated_totals.calories > 1900:
                      print("   SUCCESS: Meal plan restored to original!")
                 else:
                      print("   FAILURE: Meal plan did NOT restore fully.")
            
            # 7. Restore Workout
            print(f"[Step 6] Restoring Workout Plan...")
            workout_service.restore_workout_plan(db, user_id, event_date)
            print("   Workout Restoration Triggered.")
            
            # 8. Final Check
            print(f"[Step 7] Verifying Cleanup...")
            active = social_event_service.get_active_event(db, user_id)
            if not active or not active.is_active:
                 print("   SUCCESS: Event is no longer active.")
            else:
                 print("   FAILED: Event is still active.")
                 
        else:
            print(f"   FAILED to propose event: {proposal}")

    except Exception as e:
        print(f"\n=== Verification FAILED: {e} ===")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()
        print("\n=== Verification Complete ===")

if __name__ == "__main__":
    run_verification()
