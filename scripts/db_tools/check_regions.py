import sys
import os
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
import sys, os; from pathlib import Path; sys.path.insert(0, str([p for p in Path(__file__).resolve().parents if (p / 'backend').exists()][0] / 'backend')) # modified
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
