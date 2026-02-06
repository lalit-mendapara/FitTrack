import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from app.database import engine
from sqlalchemy import text

def debug_table():
    with engine.connect() as conn:
        print("\n=== STEP 1: Verifying Schema (Column Names) ===")
        # Query information_schema to verify exact column names in DB
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'exercises';"))
        columns = [row[0] for row in result]
        print(f"Existing Columns: {columns}")

        print("\n=== STEP 2: Proof of Concept (Insert & Select) ===")
        try:
            # Insert dummy data using QUOTED identifiers for special column names
            conn.execute(text("""
                INSERT INTO exercises ("Exercise Name", "Category", "Primary Muscle", "Difficulty", "Image URL")
                VALUES ('Debug Squat', 'Strength', 'Legs', 'Beginner', 'http://debug.com/img.jpg');
            """))
            conn.commit()
            
            # Select and display
            result = conn.execute(text('SELECT * FROM exercises;'))
            print(f"Query: SELECT * FROM exercises;")
            print("-" * 50)
            # Print Headers
            print(" | ".join(list(result.keys())))
            print("-" * 50)
            # Print Rows
            for row in result:
                print(" | ".join([str(val) for val in row]))
            print("-" * 50)
            
        except Exception as e:
            print(f"Error during insert/select: {e}")
        finally:
            print("\n=== STEP 3: Cleanup ===")
            conn.execute(text('DELETE FROM exercises WHERE "Exercise Name" = \'Debug Squat\';'))
            conn.commit()
            print("Cleanup complete. Table is empty.")

if __name__ == "__main__":
    debug_table()
