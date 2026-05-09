import sqlite3
import os

db_path = 'databases/neonplay.db'
if not os.path.exists(db_path):
    print(f"DB not found: {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print(f"Tables: {cursor.fetchall()}")
    
    # Check ingestion_logs
    cursor = conn.execute("SELECT COUNT(*) FROM ingestion_logs")
    print(f"Ingestion logs count: {cursor.fetchone()[0]}")
