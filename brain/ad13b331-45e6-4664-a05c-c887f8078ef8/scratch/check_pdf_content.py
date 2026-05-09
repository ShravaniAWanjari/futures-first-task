import sqlite3
import sys

# Set output to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('databases/neonplay.db')
cursor = conn.execute("SELECT snippet_text FROM pdf_chunks_metadata WHERE snippet_text LIKE '%subtitle%' OR snippet_text LIKE '%localization%'")
rows = cursor.fetchall()
print(f"Found {len(rows)} matching chunks.")
for r in rows[:3]:
    print(f"--- CHUNK ---\n{r[0][:200]}...")
