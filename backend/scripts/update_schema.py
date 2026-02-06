from app.database import engine
from sqlalchemy import text

def update_schema():
    with engine.connect() as conn:
        print("Adding columns to workout_logs...")
        commands = [
            "ALTER TABLE workout_logs ADD COLUMN IF NOT EXISTS img_url VARCHAR(255);",
            "ALTER TABLE workout_logs ADD COLUMN IF NOT EXISTS sets VARCHAR(50);",
            "ALTER TABLE workout_logs ADD COLUMN IF NOT EXISTS reps VARCHAR(50);",
            "ALTER TABLE workout_logs ADD COLUMN IF NOT EXISTS weight FLOAT;",
            "ALTER TABLE workout_logs ADD COLUMN IF NOT EXISTS muscle_group VARCHAR(50);",
            "ALTER TABLE workout_logs ADD COLUMN IF NOT EXISTS notes VARCHAR(255);"
        ]
        
        for cmd in commands:
            try:
                conn.execute(text(cmd))
                print(f"Executed: {cmd}")
            except Exception as e:
                print(f"Error executing {cmd}: {e}")
        
        # Manually commit if needed (though DDL is usually auto-commit in some drivers, standard engine usage might require commit)
        conn.commit()
        print("Schema update complete.")

if __name__ == "__main__":
    update_schema()
