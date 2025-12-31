from sqlalchemy import create_engine, text
from app.core.config import settings

def migrate():
    print(f"Connecting to database...")
    # Use default settings.DATABASE_URL (psycopg2)
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        try:
            print("Executing migration...")
            conn.execute(text("ALTER TABLE api_keys ADD COLUMN agent_id UUID REFERENCES agents(id) ON DELETE CASCADE;"))
            conn.commit()
            print("Migration successful: Added agent_id to api_keys table.")
        except Exception as e:
            print(f"Migration failed (might already exist): {e}")

if __name__ == "__main__":
    migrate()
