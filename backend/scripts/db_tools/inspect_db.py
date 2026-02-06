import sys
import os
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))

# Add the backend directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal

def inspect_table():
    db = SessionLocal()
    try:
        # Check columns of food_items
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'food_items'"))
        columns = [row[0] for row in result]
        print(f"Columns in food_items: {columns}")
        
        # Check count
        try:
            count = db.execute(text("SELECT count(*) FROM food_items")).scalar()
            print(f"Row count: {count}")
        except Exception as e:
            print(f"Could not count rows: {e}")
            
    except Exception as e:
        print(f"Error inspecting table: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_table()
