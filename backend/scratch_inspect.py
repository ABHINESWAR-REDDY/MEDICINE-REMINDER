import sqlite3

def check():
    conn = sqlite3.connect("pillsync.db")
    c = conn.cursor()
    schema = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='chat_messages'").fetchone()
    print("Schema:", schema[0] if schema else "None")
    rows = c.execute("SELECT id, sender_id, recipient_id, message, created_at FROM chat_messages ORDER BY id DESC LIMIT 5").fetchall()
    print("Recent rows:")
    for r in rows:
        print(r)
    conn.close()

if __name__ == "__main__":
    check()

