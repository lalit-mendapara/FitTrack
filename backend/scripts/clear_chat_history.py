import sys
import os
from sqlalchemy import text

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine

def clear_chat_history():
    print("--- 🗑️  CLEARING ALL CHAT HISTORY ---")
    try:
        with engine.connect() as connection:
            print("Executing DELETE command...")
            # Using text for raw execution
            stmt = text("TRUNCATE TABLE chat_history, chat_sessions RESTART IDENTITY;")
            result = connection.execute(stmt)
            connection.commit()
            print(f"✅ Successfully deleted all records from 'chat_history' and 'chat_sessions'.")
            
            # Optional: Reset ID counter if desired, but DELETE is sufficient.
            # stmt = text("ALTER SEQUENCE chat_history_id_seq RESTART WITH 1;")
            # connection.execute(stmt)
            # connection.commit()
            
            # Clear Redis
            try:
                import redis
                # Default local URL or fetch from config if possible
                r = redis.from_url("redis://localhost:6379/0")
                r.flushdb()
                print("✅ Successfully flushed Redis database (chat memory & questions).")
            except ImportError:
                 print("⚠️  redis-py not installed, skipping Redis clear.")
            except Exception as re_err:
                 print(f"⚠️  Failed to clear Redis: {re_err}")
            
    except Exception as e:
        print(f"❌ Failed to clear history: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Skip confirmation")
    args = parser.parse_args()

    if args.force:
        clear_chat_history()
    else:
        confirm = input("⚠️  Are you sure you want to delete ALL chat history? (y/n): ")
        if confirm.lower().startswith('y'):
            clear_chat_history()
        else:
            print("Operation cancelled.")
