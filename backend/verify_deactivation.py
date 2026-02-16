import requests
import json
from datetime import date

BASE_URL = "http://localhost:8000"
# Assuming we have a test user or can get a token. 
# For simplicity in this dev environment, I'll try to use a known user ID or login first if needed.
# However, usually I don't have the auth token easily available in a script without logging in.
# I'll assume I can use a simple login or skip auth if I can running it locally with some bypass, 
# but likely I need a token.

def login():
    # Replace with valid credentials if known, or creates a test user
    # For now, I will try to look at how other scripts did it or just assume I can't run this easily without credentials.
    # Actually, I can check `backend/tests` or similar if they exist.
    # Alternatively, I can just inspect the code logic which I have already done.
    pass

# Since I cannot easily run an authenticated request from a standalone script without setup,
# I will inspect the code logic in `feast_mode.py` and `FeastModeManager.py` very carefully instead.
# If I really need to run it, I'd need to implementing a full auth flow in the script.

# Let's try to verify the `FeastModeManager.get_deactivation_preview` method directly by invoking it in a script
# that imports the app context.

import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

from app.database import SessionLocal
from app.services.feast_mode_manager import FeastModeManager
from app.models.feast_config import FeastConfig

def verify_backend_logic():
    db = SessionLocal()
    try:
        # 1. identifying a user with active feast mode or create one
        print("Checking for active Feast Mode configurations...")
        
        from app.models.user_profile import UserProfile
        profile = db.query(UserProfile).first()
        if not profile:
             print("No user profiles found in database!")
             return
             
        user_id = profile.user_id
        print(f"Using User ID: {user_id}")
        
        manager = FeastModeManager(db)
        
        # Ensure we have an active config
        config = manager.get_active_config(user_id)
        if not config:
            print("No active config for user 1. Creating a dummy one...")
            # Create a dummy active config
            proposal = {
                "event_name": "Test Event",
                "event_date": date.today(), # Event is today
                "daily_deduction": 500,
                "total_banked": 1000,
                "start_date": date.today(),
                "custom_deduction": 0
            }
            manager.activate(user_id, proposal, workout_boost=False)
            print("Created dummy Feast Mode.")
        
        # 2. Test Deactivation Preview
        print("\nTesting Deactivation Preview...")
        preview = manager.get_deactivation_preview(user_id)
        print(f"Preview Result: {json.dumps(preview, default=str, indent=2)}")
        
        if "error" in preview:
            print("ERROR: Preview failed.")
        else:
             print("SUCCESS: Preview generated.")
             
        # 3. Test Cancellation
        print("\nTesting Cancellation...")
        result = manager.cancel(user_id)
        print(f"Cancel Result: {result}")
        
        # Verify it's gone
        config_after = manager.get_active_config(user_id)
        if config_after is None:
            print("SUCCESS: Feast Mode cancelled.")
        else:
            print("ERROR: Feast Mode still active.")
            
    except Exception as e:
        print(f"Global Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_backend_logic()
