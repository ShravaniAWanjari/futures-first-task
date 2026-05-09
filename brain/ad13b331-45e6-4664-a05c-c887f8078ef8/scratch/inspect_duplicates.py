import sqlite3
conn = sqlite3.connect('databases/neonplay.db')
cursor = conn.execute("SELECT COUNT(*) FROM ingestion_logs WHERE message LIKE '%duplicate%'")
print(f"Duplicates: {cursor.fetchone()[0]}")

cursor = conn.execute("SELECT log_level, action_taken, COUNT(*) FROM ingestion_logs WHERE message LIKE '%duplicate%' GROUP BY log_level, action_taken")
print(f"Duplicate distribution: {cursor.fetchall()}")
