"""Migration script to safely transfer all data from SQLite (pillsync.db) into PostgreSQL (myproject)."""

import sqlite3
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine
from app.models import Base

def migrate():
    sqlite_path = "pillsync.db"
    print(f"Connecting to SQLite: {sqlite_path}")
    sq_conn = sqlite3.connect(sqlite_path)
    sq_conn.row_factory = sqlite3.Row
    sq_cur = sq_conn.cursor()

    # Ensure PostgreSQL tables exist
    print("Ensuring PostgreSQL schema and tables exist...")
    Base.metadata.create_all(bind=engine)

    # Ordered list of tables to respect foreign keys
    tables = [
        "users",
        "system_settings",
        "email_verification_codes",
        "medicine_references",
        "conditions",
        "prescriptions",
        "ocr_jobs",
        "medicines",
        "medication_schedules",
        "caregiver_patient_assignments",
        "medication_doses",
        "audit_logs",
        "chat_messages",
        "notifications",
    ]

    with engine.connect() as pg_conn:
        with pg_conn.begin():
            for table in tables:
                # Check if table exists in SQLite
                sq_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not sq_cur.fetchone():
                    print(f"Skipping {table} (not found in SQLite)")
                    continue

                sq_cur.execute(f'SELECT * FROM "{table}"')
                rows = sq_cur.fetchall()
                if not rows:
                    print(f"Table '{table}': 0 rows in SQLite (skipped)")
                    continue

                col_names = list(rows[0].keys())
                print(f"Migrating table '{table}': {len(rows)} rows...")

                # Prepare insert statement
                cols_str = ", ".join(f'"{c}"' for c in col_names)
                placeholders = ", ".join(f":{c}" for c in col_names)
                insert_sql = text(f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING')

                # Execute in batches if large
                batch_size = 1000
                data = [dict(row) for row in rows]
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    pg_conn.execute(insert_sql, batch)

                print(f"✓ Table '{table}' migrated ({len(rows)} records)")

                # Reset PostgreSQL sequence for auto-increment ID if table has 'id' column
                if "id" in col_names:
                    try:
                        pg_conn.execute(text(f"""
                            SELECT setval(
                                pg_get_serial_sequence('"{table}"', 'id'),
                                COALESCE((SELECT MAX(id) FROM "{table}"), 1),
                                true
                            );
                        """))
                    except Exception as seq_err:
                        print(f"  Note: Could not update sequence for {table}: {seq_err}")

    sq_conn.close()
    print("\n=== ALL DATA SUCCESSFULLY MIGRATED TO POSTGRESQL ===")

if __name__ == "__main__":
    migrate()
