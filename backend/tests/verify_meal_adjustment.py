import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.database import SessionLocal
from app.services.ai_coach import FitnessCoachService
from app.services.chat_memory_service import ChatMemoryService
from app.models.user_profile import UserProfile
from app.models.meal_plan import MealPlan

# Mock State
class MockState(dict):
    pass

async def test_meal_adjustment_flow():
    db = SessionLocal()
    try:
        # 1. Setup - Ensure a user exists and has a meal plan
        print("--- SETUP ---")
        user = db.query(UserProfile).first()
        if not user:
            print("No user found! Please generate a plan first.")
            return

        user_id = user.user_id
        print(f"Testing with User ID: {user_id}")
        
        # Ensure plan exists
        plan = db.query(MealPlan).filter(MealPlan.user_profile_id == user.id).first()
        if not plan:
             print("No meal plan found for user.")
             return
        
        # Debug Meals
        meals = db.query(MealPlan).filter(MealPlan.user_profile_id == user.id).all()
        print("Available Meals:")
        for m in meals:
            print(f" - ID: {m.meal_id}, Label: {m.label}")
             
        session_id = f"test_session_{int(datetime.now().timestamp())}"
        print(f"Session ID: {session_id}")
        
        # Initialize Service
        service = FitnessCoachService(db, session_id)
        
        # 2. Test Detection (Proposal)
        print("\n--- TEST: DETECT INTENT (PROPOSAL) ---")
        msg = "I'm eating out for lunch, it will be about 1200 calories having pizza"
        state = {"user_message": msg, "user_id": user_id, "session_id": session_id}
        
        result = await service._node_detect_intent(state)
        print(f"Detection Result: {result.keys()}")
        
        adj_data = result.get("meal_adjustment_data")
        if not adj_data or adj_data.get("type") != "proposal":
            print("❌ Failed to detect meal adjustment proposal")
            print(result)
            return
            
        print(f"✅ Detected: {adj_data}")
        
        # 3. Test Process (Proposal)
        print("\n--- TEST: PROCESS PROPOSAL ---")
        state["meal_adjustment_data"] = adj_data
        
        # This should generate a response and save to memory
        process_res = await service._node_process_meal_adjustment(state)
        print(f"Process Response: {process_res.get('final_response')}")
        
        # Check Memory
        memory = ChatMemoryService(session_id)
        pending = memory.get_session_data("pending_meal_adjustment")
        if not pending:
            print("❌ Failed to save pending adjustment to memory")
            return
            
        print(f"✅ Saved to Memory: {pending}")
        
        # Simulate AI Message in Memory (so detection works next step)
        # We need to manually inject the AI response into history/memory for `get_last_ai_message` to work?
        # ChatMemoryService 'get_last_ai_message' reads from Redis 'history' list usually.
        # But `_node_process_meal_adjustment` returns response, it doesn't write to memory history automatically (the graph runner normally does).
        # We must simulate the graph runner saving the AI message.
        
        # Simulate AI Message in Memory (so detection works next step)
        try:
             memory.add_ai_message(process_res['final_response'])
             print("✅ Injected AI response into memory")
        except Exception as e:
             print(f"❌ Failed to inject memory: {e}")
        
        # 4. Test Detection (Confirmation)
        print("\n--- TEST: DETECT INTENT (CONFIRMATION) ---")
        confirm_msg = "Yes, update it"
        state["user_message"] = confirm_msg
        
        # Detect again
        confirm_res = await service._node_detect_intent(state)
        print(f"Confirm Detection Result: {confirm_res.keys()}")
        
        confirm_data = confirm_res.get("meal_adjustment_data")
        if not confirm_data or confirm_data.get("type") != "confirm":
             print("❌ Failed to detect confirmation")
             print(f"Last AI Msg in Mem: {memory.get_last_ai_message()}")
             print(confirm_res)
             return
             
        print(f"✅ Detected Confirmation: {confirm_data}")
        
        # 5. Test Process (Execution)
        print("\n--- TEST: PROCESS EXECUTION ---")
        state["meal_adjustment_data"] = confirm_data
        
        exec_res = await service._node_process_meal_adjustment(state)
        print(f"Execution Response: {exec_res.get('final_response')}")
        
        # 6. Verify DB
        print("\n--- TEST: DB VERIFICATION ---")
        # Re-fetch plan
        # We adjusted 'dinner' likely (default if not specified, or parsed from 'dinner')
        # adj_data had 'target_meal'.
        target_meal = pending['target_meal'].lower()
        print(f"Checking meal: {target_meal}")
        
        updated_meal = db.query(MealPlan).filter(
            MealPlan.user_profile_id == user.id, 
            MealPlan.label.ilike(target_meal)
        ).first()
        
        if updated_meal and updated_meal.is_user_adjusted:
             print(f"✅ Meal '{updated_meal.dish_name}' is_user_adjusted=True")
             print(f"   Calories: {updated_meal.nutrients['calories']}")
             print(f"   Note: {updated_meal.adjustment_note}")
        else:
             print("❌ Meal was not updated in DB!")
             if updated_meal:
                 print(f"   is_user_adjusted: {updated_meal.is_user_adjusted}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_meal_adjustment_flow())
