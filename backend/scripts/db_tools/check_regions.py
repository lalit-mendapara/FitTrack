import sys
import os
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.database import SessionLocal

def check_regions():
    db = SessionLocal()
    try:
        regions = db.execute(text("SELECT DISTINCT region FROM food_items")).fetchall()
        print(f"Regions: {regions}")
    finally:
        db.close()

if __name__ == "__main__":
    check_regions()
