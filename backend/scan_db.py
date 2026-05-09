import sqlite3
import os

db_path = 'C:/Users/shrav/Desktop/12 week thing/futures-first/databases/neonplay.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

target_val = 1001944260

print(f"Scanning {db_path} for {target_val}...")

for table in tables:
    try:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        for row in rows:
            if target_val in row or str(target_val) in [str(v) for v in row]:
                print(f"Found in {table}: {row}")
    except Exception as e:
        print(f"Error scanning {table}: {e}")

conn.close()
