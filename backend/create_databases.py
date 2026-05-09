import sqlite3
import os
from pathlib import Path
from backend.config import Config

def create_databases():
    # Base directory is the current script's directory
    base_dir = Path(__file__).resolve().parent
    
    # Create required folder structure
    folders = [
        Path(Config.VISTASTREAM_DB_PATH).parent,
        Path(Config.LOG_DIR_PATH),
        Path(Config.CHROMA_DB_PATH)
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"Ensured directory exists: {folder}")

    # DB naming clearly differentiating environments
    db_paths = [Config.VISTASTREAM_DB_PATH, Config.NEONPLAY_DB_PATH, Config.SESSIONS_DB_PATH]
    schema_path = base_dir / "schema.sql"

    if not schema_path.exists():
        print(f"Error: {schema_path} not found. Cannot initialize databases.")
        return

    # Read the schema file
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Create both DBs and execute schema.sql
    for db_path_str in db_paths:
        db_path = Path(db_path_str)
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Enable foreign key support
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            # Execute schema.sql to initialize empty tables (idempotent script)
            # Sessions DB might not need the schema, but we execute it anyway or we can separate it.
            # Usually sessions.db has its own schema or is managed by langchain, but doing schema.sql is safe if it uses IF NOT EXISTS
            cursor.executescript(schema_sql)
            conn.commit()
            
            print(f"Successfully initialized SQLite database: {db_path}")
        except sqlite3.Error as e:
            print(f"Error initializing database {db_path}: {e}")
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    create_databases()
