
import sys, os; from pathlib import Path; sys.path.insert(0, str([p for p in Path(__file__).resolve().parents if (p / 'backend').exists()][0] / 'backend')) # modified

from app.database import engine
from sqlalchemy import inspect

def check_tables():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("Existing Tables:", tables)
    
    if "feast_configs" in tables:
        print("PASS: feast_configs table exists.")
    else:
        print("FAIL: feast_configs table MISSING.")

if __name__ == "__main__":
    check_tables()
