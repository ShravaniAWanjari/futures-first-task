import sqlite3
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.config import Config

def fix_neonplay_data():
    db_path = Config.NEONPLAY_DB_PATH
    print(f"Connecting to {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Identify rows with NULL or empty region
    cursor.execute("SELECT campaign_id, campaign_name, region, spend_usd FROM marketing_campaigns WHERE region IS NULL OR region = ''")
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} rows with missing regions.")
    
    for rid, name, region, spend in rows:
        # Heuristic: If it has 1B spend, it's definitely CAM030 or similar anomaly
        if spend >= 100_000_000:
            print(f" -> Deleting anomaly {rid} ({name}) with spend {spend}")
            cursor.execute("DELETE FROM marketing_campaigns WHERE campaign_id = ?", (rid,))
        else:
            # Try to infer region from name or just set to 'Unknown' (or re-run ingestion properly)
            # In this case, we know NA was being lost.
            print(f" -> Fixing {rid} ({name}): Setting region to 'North America' (Recovered from NA)")
            cursor.execute("UPDATE marketing_campaigns SET region = 'North America' WHERE campaign_id = ?", (rid,))
            
    conn.commit()
    print("Database cleanup complete.")
    conn.close()

if __name__ == "__main__":
    fix_neonplay_data()
