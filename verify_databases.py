import sqlite3
import os

def verify():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_names = ["vistastream.db", "neonplay.db"]
    
    expected_tables = {
        "movies", "viewers", "watch_activity", "reviews", 
        "marketing_campaigns", "regional_performance", 
        "ingestion_logs", "pdf_chunks_metadata"
    }

    for db_name in db_names:
        print(f"\n--- Verifying {db_name} ---")
        db_path = os.path.join(base_dir, "databases", db_name)
        if not os.path.exists(db_path):
            print(f"ERROR: {db_name} not found.")
            continue
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verify PRAGMA
        cursor.execute("PRAGMA foreign_keys;")
        fk_status = cursor.fetchone()[0]
        print(f"PRAGMA foreign_keys: {'ON' if fk_status == 1 else 'OFF'}")
        # Note: If we just connected, it might be OFF by default unless we set it.
        # So let's enable it just like an app would:
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA foreign_keys;")
        print(f"PRAGMA foreign_keys (after setting): {'ON' if cursor.fetchone()[0] == 1 else 'OFF'}")

        # Verify Tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        missing = expected_tables - tables
        if not missing:
            print(f"Tables verification: PASS (Found all {len(expected_tables)} tables)")
        else:
            print(f"Tables verification: FAIL. Missing: {missing}")
            
        # Verify Foreign Keys
        print("\nForeign Keys:")
        for table in ["watch_activity", "reviews"]:
            cursor.execute(f"PRAGMA foreign_key_list({table});")
            fks = cursor.fetchall()
            for fk in fks:
                # fk is (id, seq, table, from, to, on_update, on_delete, match)
                print(f"  {table}.{fk[3]} -> {fk[2]}.{fk[4]}")

        conn.close()

if __name__ == "__main__":
    verify()
