import sqlite3
import os

def create_databases():
    # Base directory is the current script's directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create required folder structure
    folders = ["databases", "logs", "chroma"]
    for folder in folders:
        os.makedirs(os.path.join(base_dir, folder), exist_ok=True)
        print(f"Ensured directory exists: {folder}/")

    # DB naming clearly differentiating environments
    db_names = ["vistastream.db", "neonplay.db"]
    schema_path = os.path.join(base_dir, "schema.sql")

    if not os.path.exists(schema_path):
        print(f"Error: {schema_path} not found. Cannot initialize databases.")
        return

    # Read the schema file
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Create both DBs and execute schema.sql
    for db_name in db_names:
        db_path = os.path.join(base_dir, "databases", db_name)
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Enable foreign key support
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            # Execute schema.sql to initialize empty tables (idempotent script)
            cursor.executescript(schema_sql)
            conn.commit()
            
            print(f"Successfully initialized SQLite database: databases/{db_name}")
        except sqlite3.Error as e:
            print(f"Error initializing databases/{db_name}: {e}")
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    create_databases()
