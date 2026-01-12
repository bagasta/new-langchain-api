from sqlalchemy import create_engine, text
from app.core.config import settings

def migrate():
    print(f"Connecting to database...")
    # Use default settings.DATABASE_URL (psycopg2)
    engine = create_engine(settings.DATABASE_URL)
    with engine.begin() as conn:
        try:
            print("Executing migration...")
            # Fix missing updated_at column in agent_system_message_history
            conn.execute(text("ALTER TABLE agent_system_message_history ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;"))
            # conn.commit() is automatic with engine.begin()
            print("Migration successful: Added updated_at to agent_system_message_history table.")
        except Exception as e:
            print(f"Migration failed (might already exist): {e}")

if __name__ == "__main__":
    migrate()
