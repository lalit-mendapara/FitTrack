import sys
import os
from sqlalchemy import text

# Add the parent directory to sys.path so we can import app modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.database import engine

def add_columns():
    with engine.connect() as connection:
        # Commit manually if needed, or use autocommit
        trans = connection.begin()
        try:
            print("Checking schema for 'meal_plans' table...")
            
            # Check if columns exist (postgres specific check)
            check_sql = text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'meal_plans';
            """)
            result = connection.execute(check_sql)
            columns = [row[0] for row in result.fetchall()]
            
            print(f"Current columns: {columns}")
            
            if 'created_at' not in columns:
                print("Adding 'created_at' column...")
                connection.execute(text("ALTER TABLE meal_plans ADD COLUMN created_at TIMESTAMP DEFAULT now();"))
            else:
                print("'created_at' already exists.")
                
            if 'updated_at' not in columns:
                print("Adding 'updated_at' column...")
                connection.execute(text("ALTER TABLE meal_plans ADD COLUMN updated_at TIMESTAMP DEFAULT now();"))
            else:
                print("'updated_at' already exists.")
                
            trans.commit()
            print("Schema update completed successfully.")
            
        except Exception as e:
            trans.rollback()
            print(f"Error updating schema: {e}")
            raise e

if __name__ == "__main__":
    add_columns()
