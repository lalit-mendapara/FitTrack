import sys
import os
import logging
from datetime import datetime
import pytz

# Add project root to path
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.user_profile import UserProfile

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_scheduler_logic():
    print(f"--- Manual Scheduler Configuration Test ---")
    print(f"System Time (Container): {datetime.now()}")
    print(f"System UTC Time: {datetime.utcnow()}")
    
    db = SessionLocal()
    try:
        profiles = db.query(UserProfile).all()
        print(f"Found {len(profiles)} user profiles.")
        
        for profile in profiles:
            user_tz_str = profile.timezone or "UTC"
            print(f"\nUser {profile.user_id}:")
            # print(f"  - Configured Timezone: {user_tz_str}")
            
            try:
                tz = pytz.timezone(user_tz_str)
                user_now = datetime.now(tz)
                print(f"  - User Local Time: {user_now}")
                print(f"  - User Local Hour: {user_now.hour}")
                
                if user_now.hour == 9:
                    print(f"  - [MATCH] This user WOULD trigger the task now!")
                else:
                    print(f"  - [NO MATCH] Hour is not 9.")
                    
            except Exception as e:
                print(f"  - Error processing timezone: {e}")
                
    except Exception as e:
        print(f"Database Error: {e}")
    finally:
        db.close()
    
    print("\n--- End Test ---")

if __name__ == "__main__":
    test_scheduler_logic()
