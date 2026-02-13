import asyncio
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import date, timedelta
import dataclasses  # Ensure dataclasses is imported if needed by dependencies

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Minimal mocks to satisfy imports
class MockSession:
    def __init__(self):
        self.query_results = {}
        self.added = []
        self.committed = False
    
    def query(self, *args):
        return self
        
    def filter(self, *args, **kwargs):
        return self
        
    def first(self):
        return None
        
    def all(self):
        return []

    def add(self, item):
        self.added.append(item)
        
    def commit(self):
        self.committed = True

async def test_custom_deduction_flow():
    print("--- STARTING TEST ---")
    
    # We need to mock imports inside ai_coach to avoid side effects
    with patch('app.services.social_event_service.propose_banking_strategy') as mock_propose, \
         patch('app.services.ai_coach.ChatMemoryService') as MockMemoryClass, \
         patch('app.services.social_event_service.create_social_event') as mock_create:
        
        # Configure Mock Memory Instance
        mock_memory_instance = MagicMock()
        MockMemoryClass.return_value = mock_memory_instance
        
        # Simulate that we have a pending event with a CUSTOM deduction (e.g. 300)
        # DIFFERENT from default (which is usually calculated based on date)
        mock_memory_instance.get_session_data.return_value = {
            "event_name": "Pizza Party",
            "event_date": "2026-02-20",
            "daily_deduction": 300 # CUSTOM VALUE
        }
        
        # Configure Propose Mock to return valid proposal
        def side_effect_propose(db, user_id, event_date, event_name, custom_deduction=None):
            print(f"Called propose with custom_deduction={custom_deduction}")
            # Identify if the fix worked
            if custom_deduction == 300:
                 print("✅ Logic correctly retrieved custom_deduction=300")
            elif custom_deduction is None:
                 print("❌ Logic failed! custom_deduction is None (Defaulting)")
            else:
                 print(f"❓ Logic passed custom_deduction={custom_deduction}")
                 
            return {
                "event_name": event_name,
                "event_date": event_date,
                "days_remaining": 5,
                "daily_deduction": custom_deduction or 500, # If None, default 500
                "total_banked": (custom_deduction or 500) * 5,
                "start_date": date.today()
            }
        mock_propose.side_effect = side_effect_propose

        # Import Service (it will use patched modules)
        from app.services.ai_coach import FitnessCoachService
        
        # Mock DB
        mock_db = MockSession()
        service = FitnessCoachService(mock_db, "test_session")
        
        # Mock internal components to avoid actual DB calls
        service.stats_service = MagicMock()
        service.stats_service.get_full_user_context.return_value = {}
        service.stats_service.get_user_profile.return_value = {"caloric_target": 2000}
        
        # Prepare State
        state = {
            "user_id": 123,
            "session_id": "test_session",
            "social_event_data": {
                "type": "confirm",
                "event_name": "Pizza Party",
                "event_date": date(2026, 2, 20),
                "skip_workout": False
            }
        }
        
        # RUN
        print("\n--- RUNNING _node_process_social_event ---")
        try:
            await service._node_process_social_event(state)
        except Exception as e:
            print(f"Error during execution (might be expected due to deep mocks): {e}")
            
        # VERIFY
        # Check if propose_banking_strategy was called with custom_deduction=300
        calls = mock_propose.call_args_list
        if not calls:
            print("❌ propose_banking_strategy was NOT called!")
        else:
            last_call = calls[-1]
            args, kwargs = last_call
            captured = kwargs.get('custom_deduction')
            print(f"\nFinal Verify: captured custom_deduction={captured}")
            if captured == 300:
                print("🏆 SUCCESS: The fix addresses the issue.")
            else:
                print("💥 FAILURE: The fix did not work.")

    print("\n--- TEST CASE 2: CUSTOMIZE FLOW ---")
    # Test Scenario B: Customize
    # User says "Make it 300 kcal" -> Handler should save 300 to memory
    
    with patch('app.services.social_event_service.propose_banking_strategy') as mock_propose_cust, \
         patch('app.services.ai_coach.ChatMemoryService') as MockMemoryClassCust:
         
        mock_mem = MagicMock()
        MockMemoryClassCust.return_value = mock_mem
        
        # Propose returns a sanitized deduction
        mock_propose_cust.return_value = {
            "event_name": "Party",
            "event_date": date(2026,2,20),
            "daily_deduction": 300, # Sanitized return
            "total_banked": 1500,
            "start_date": date.today()
        }
        
        state_cust = {
            "user_id": 123,
            "session_id": "test_session_2",
            "social_event_data": {
                "type": "customize",
                "event_name": "Party",
                "event_date": date(2026, 2, 20),
                "custom_deduction": 298 # User input (weird number)
            }
        }
        
        # Re-init service
        mock_db = MockSession()
        from app.services.ai_coach import FitnessCoachService
        service = FitnessCoachService(mock_db, "test_session_2")
        
        await service._node_process_social_event(state_cust)
        
        # Verify Memory Save
        # Should have saved 300 (from proposal), not 298
        mock_mem.set_session_data.assert_called()
        args, kwargs = mock_mem.set_session_data.call_args
        key = args[0]
        saved_data = args[1]
        
        print(f"Customize Saved: {saved_data}")
        if saved_data.get("daily_deduction") == 300:
             print("✅ TEST PASSED: Saved sanitized deduction (300) instead of raw (298)")
        else:
             print(f"❌ TEST FAILED: Saved {saved_data.get('daily_deduction')} instead of 300")

if __name__ == "__main__":
    asyncio.run(test_custom_deduction_flow())
