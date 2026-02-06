from sqlalchemy import text
from app.database import engine

def update_schema():
    with engine.connect() as connection:
        # 1. Add timezone column to user_profiles
        try:
            print("Adding timezone column to user_profiles...")
            connection.execute(text("ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC';"))
            print("Timezone column added.")
        except Exception as e:
            print(f"Error adding timezone column: {e}")

        # 2. Create notifications table
        try:
            print("Creating notifications table...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    message VARCHAR(255) NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    type VARCHAR(50) DEFAULT 'info',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            print("Notifications table created.")
        except Exception as e:
            print(f"Error creating notifications table: {e}")
        
        connection.commit()

if __name__ == "__main__":
    update_schema()
