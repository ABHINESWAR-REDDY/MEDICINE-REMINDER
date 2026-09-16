from sqlalchemy import text
from app.core.database import engine

def migrate():
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en';"))
        conn.commit()
        print("MIGRATION_SUCCESS: users.language column verified/added successfully.")

if __name__ == "__main__":
    migrate()
