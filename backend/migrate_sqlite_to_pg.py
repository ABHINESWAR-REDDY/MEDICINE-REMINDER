"""
Migration script to safely copy all historical data from SQLite (backend/pillsync.db)
to PostgreSQL (myproject), preserving all user accounts, passwords, relations, and resetting sequences.
"""

import sqlite3
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch, Json

def migrate():
    sqlite_path = r"c:\Users\admin\Desktop\pillsync\backend\pillsync.db"
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sq_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect("host=localhost port=5432 user=postgres password=root123 dbname=myproject")
    pg_cur = pg_conn.cursor()

    print("Connected to SQLite and PostgreSQL.")

    # 1. USERS
    sq_cur.execute("SELECT * FROM users ORDER BY id ASC;")
    users = sq_cur.fetchall()
    print(f"Migrating {len(users)} users...")
    for u in users:
        pg_cur.execute("""
            INSERT INTO users (id, employee_id, name, email, password_hash, role, approval_status, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                employee_id = EXCLUDED.employee_id,
                name = EXCLUDED.name,
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role,
                approval_status = EXCLUDED.approval_status,
                is_active = EXCLUDED.is_active,
                updated_at = EXCLUDED.updated_at;
        """, (
            u['id'], u['employee_id'], u['name'], u['email'], u['password_hash'],
            u['role'], u['approval_status'], bool(u['is_active']), u['created_at'], u['updated_at']
        ))
    pg_conn.commit()

    # 2. MEDICINE REFERENCES
    sq_cur.execute("SELECT * FROM medicine_references ORDER BY id ASC;")
    med_refs = sq_cur.fetchall()
    print(f"Migrating {len(med_refs)} medicine_references...")
    med_ref_data = [
        (r['id'], r['name'], r['normalized_name'], r['category'], r['dosage_form'],
         r['strength'], r['manufacturer'], r['indication'], r['classification'],
         r['frequency'], r['created_at'], r['updated_at'])
        for r in med_refs
    ]
    execute_batch(pg_cur, """
        INSERT INTO medicine_references (id, name, normalized_name, category, dosage_form, strength, manufacturer, indication, classification, frequency, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING;
    """, med_ref_data, page_size=2000)
    pg_conn.commit()

    # 3. SYSTEM SETTINGS
    sq_cur.execute("SELECT * FROM system_settings ORDER BY id ASC;")
    settings = sq_cur.fetchall()
    print(f"Migrating {len(settings)} system_settings...")
    for s in settings:
        val = s['value']
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except:
                pass
        pg_cur.execute("""
            INSERT INTO system_settings (id, key, value, description, category, updated_at, updated_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                key = EXCLUDED.key,
                value = EXCLUDED.value,
                description = EXCLUDED.description,
                category = EXCLUDED.category,
                updated_at = EXCLUDED.updated_at,
                updated_by = EXCLUDED.updated_by;
        """, (s['id'], s['key'], Json(val), s['description'], s['category'], s['updated_at'], s['updated_by']))
    pg_conn.commit()

    # 4. CONDITIONS
    sq_cur.execute("SELECT * FROM conditions ORDER BY id ASC;")
    conds = sq_cur.fetchall()
    print(f"Migrating {len(conds)} conditions...")
    for c in conds:
        pg_cur.execute("""
            INSERT INTO conditions (id, user_id, name, description, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (c['id'], c['user_id'], c['name'], c['description'], c['created_at'], c['updated_at']))
    pg_conn.commit()

    # 5. PRESCRIPTIONS
    sq_cur.execute("SELECT * FROM prescriptions ORDER BY id ASC;")
    prescs = sq_cur.fetchall()
    print(f"Migrating {len(prescs)} prescriptions...")
    for p in prescs:
        pg_cur.execute("""
            INSERT INTO prescriptions (id, user_id, prescription_number, doctor_name, issue_date, expiry_date, notes, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (p['id'], p['user_id'], p['prescription_number'], p['doctor_name'], p['issue_date'], p['expiry_date'], p['notes'], p['status'], p['created_at'], p['updated_at']))
    pg_conn.commit()

    # 6. MEDICINES
    sq_cur.execute("SELECT * FROM medicines ORDER BY id ASC;")
    meds = sq_cur.fetchall()
    print(f"Migrating {len(meds)} medicines...")
    for m in meds:
        pg_cur.execute("""
            INSERT INTO medicines (id, user_id, prescription_id, condition_id, name, dosage_amount, dosage_unit, quantity, medicine_form, instructions, start_date, end_date, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (m['id'], m['user_id'], m['prescription_id'], m['condition_id'], m['name'], m['dosage_amount'], m['dosage_unit'], m['quantity'], m['medicine_form'], m['instructions'], m['start_date'], m['end_date'], bool(m['is_active']), m['created_at'], m['updated_at']))
    pg_conn.commit()

    # 7. MEDICATION SCHEDULES
    sq_cur.execute("SELECT * FROM medication_schedules ORDER BY id ASC;")
    scheds = sq_cur.fetchall()
    print(f"Migrating {len(scheds)} medication_schedules...")
    for sc in scheds:
        sched_times = sc['scheduled_times']
        if isinstance(sched_times, str):
            try:
                sched_times = json.loads(sched_times)
            except:
                pass
        pg_cur.execute("""
            INSERT INTO medication_schedules (id, medicine_id, frequency_type, times_per_day, scheduled_times, dose_quantity, start_date, end_date, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (sc['id'], sc['medicine_id'], sc['frequency_type'], sc['times_per_day'], Json(sched_times), sc['dose_quantity'], sc['start_date'], sc['end_date'], bool(sc['is_active']), sc['created_at'], sc['updated_at']))
    pg_conn.commit()

    # 8. CAREGIVER PATIENT ASSIGNMENTS
    sq_cur.execute("SELECT * FROM caregiver_patient_assignments ORDER BY id ASC;")
    cpas = sq_cur.fetchall()
    print(f"Migrating {len(cpas)} caregiver_patient_assignments...")
    for a in cpas:
        pg_cur.execute("""
            INSERT INTO caregiver_patient_assignments (id, caregiver_id, patient_id, status, assigned_by, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (a['id'], a['caregiver_id'], a['patient_id'], a['status'], a['assigned_by'], a['created_at'], a['updated_at']))
    pg_conn.commit()

    # 9. MEDICATION DOSES
    sq_cur.execute("SELECT * FROM medication_doses ORDER BY id ASC;")
    doses = sq_cur.fetchall()
    print(f"Migrating {len(doses)} medication_doses...")
    for d in doses:
        pg_cur.execute("""
            INSERT INTO medication_doses (id, schedule_id, medicine_id, patient_id, scheduled_time, actual_time, status, recorded_by, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (d['id'], d['schedule_id'], d['medicine_id'], d['patient_id'], d['scheduled_time'], d['actual_time'], d['status'], d['recorded_by'], d['created_at'], d['updated_at']))
    pg_conn.commit()

    # 10. OCR JOBS
    sq_cur.execute("SELECT * FROM ocr_jobs ORDER BY created_at ASC;")
    jobs = sq_cur.fetchall()
    print(f"Migrating {len(jobs)} ocr_jobs...")
    for j in jobs:
        pg_cur.execute("""
            INSERT INTO ocr_jobs (id, user_id, status, stage, progress_message, created_at, started_at, completed_at, error_code, error_message, result_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (j['id'], j['user_id'], j['status'], j['stage'], j['progress_message'], j['created_at'], j['started_at'], j['completed_at'], j['error_code'], j['error_message'], j['result_json']))
    pg_conn.commit()

    # 11. AUDIT LOGS
    sq_cur.execute("SELECT * FROM audit_logs ORDER BY id ASC;")
    audits = sq_cur.fetchall()
    print(f"Migrating {len(audits)} audit_logs...")
    for a in audits:
        det = a['details']
        if isinstance(det, str):
            try:
                det = json.loads(det)
            except:
                pass
        pg_cur.execute("""
            INSERT INTO audit_logs (id, actor_user_id, action, target_type, target_id, details, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (a['id'], a['actor_user_id'], a['action'], a['target_type'], a['target_id'], Json(det), a['created_at']))
    pg_conn.commit()

    # 12. CHAT MESSAGES
    sq_cur.execute("SELECT * FROM chat_messages ORDER BY id ASC;")
    chats = sq_cur.fetchall()
    print(f"Migrating {len(chats)} chat_messages...")
    for ch in chats:
        pg_cur.execute("""
            INSERT INTO chat_messages (id, sender_id, recipient_id, message, is_read, is_deleted, deleted_at, deleted_by, cleared_by_sender, cleared_by_recipient, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (ch['id'], ch['sender_id'], ch['recipient_id'], ch['message'], bool(ch['is_read']), bool(ch['is_deleted']), ch['deleted_at'], ch['deleted_by'], bool(ch['cleared_by_sender']), bool(ch['cleared_by_recipient']), ch['created_at'], ch['updated_at']))
    pg_conn.commit()

    # 13. NOTIFICATIONS
    sq_cur.execute("SELECT * FROM notifications ORDER BY id ASC;")
    notifs = sq_cur.fetchall()
    print(f"Migrating {len(notifs)} notifications...")
    for n in notifs:
        pg_cur.execute("""
            INSERT INTO notifications (id, user_id, type, title, message, severity, related_dose_id, related_medicine_id, is_read, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (n['id'], n['user_id'], n['type'], n['title'], n['message'], n['severity'], n['related_dose_id'], n['related_medicine_id'], bool(n['is_read']), n['created_at'], n['updated_at']))
    pg_conn.commit()

    # 14. EMAIL VERIFICATION CODES
    sq_cur.execute("SELECT * FROM email_verification_codes ORDER BY id ASC;")
    otps = sq_cur.fetchall()
    print(f"Migrating {len(otps)} email_verification_codes...")
    for o in otps:
        pg_cur.execute("""
            INSERT INTO email_verification_codes (id, email, code_hash, purpose, expires_at, attempts, is_used, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (o['id'], o['email'], o['code_hash'], o['purpose'], o['expires_at'], o['attempts'], bool(o['is_used']), o['created_at']))
    pg_conn.commit()

    # 15. RESET ALL SEQUENCES TO MAX(id)
    serial_tables = [
        'users', 'medicine_references', 'system_settings', 'conditions',
        'prescriptions', 'medicines', 'medication_schedules',
        'caregiver_patient_assignments', 'medication_doses',
        'audit_logs', 'chat_messages', 'notifications', 'email_verification_codes'
    ]
    for table in serial_tables:
        pg_cur.execute(f"SELECT MAX(id) FROM {table};")
        max_id = pg_cur.fetchone()[0]
        if max_id:
            seq_name = f"{table}_id_seq"
            pg_cur.execute(f"SELECT setval('{seq_name}', %s, true);", (max_id,))
            print(f"Sequence {seq_name} reset to {max_id}")
    pg_conn.commit()

    print("MIGRATION COMPLETED SUCCESSFULLY!")
    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    migrate()
