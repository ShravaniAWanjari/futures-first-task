import sqlite3
import os
import time
import json
import logging
from typing import Dict, Any, List, Optional
from backend.config import Config

# Configure basic logging for health diagnostics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("health_check")

def get_db_size(db_path: str) -> str:
    """Returns human-readable database size."""
    if not os.path.exists(db_path):
        return "0 KB"
    size_bytes = os.path.getsize(db_path)
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def check_sqlite_health(db_path: str) -> Dict[str, Any]:
    if not os.path.exists(db_path):
        return {
            "status": "unhealthy", 
            "error_type": "database_file_missing",
            "message": f"Database file not found at {db_path}",
            "suggested_fix": "Run bootstrap.py to initialize databases."
        }
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        
        # Get counts for some tables to ensure data exists
        cursor.execute("SELECT COUNT(*) FROM movies")
        movies = cursor.fetchone()[0]
        
        # Get warning counts from ingestion logs
        cursor.execute("SELECT COUNT(*) FROM ingestion_logs WHERE log_level = 'WARNING'")
        warnings = cursor.fetchone()[0]
        
        # Get last ingestion timestamp
        cursor.execute("SELECT MAX(timestamp) FROM ingestion_logs")
        last_ingest = cursor.fetchone()[0]
        
        conn.close()
        return {
            "status": "healthy",
            "size": get_db_size(db_path),
            "row_counts": {"movies": movies},
            "warnings": warnings,
            "last_ingestion": last_ingest
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error_type": "database_connection_failed",
            "message": str(e),
            "suggested_fix": "Ensure the database is not locked or corrupted."
        }

def check_chroma_health(target_dataset: str) -> Dict[str, Any]:
    """
    Categorized health states for Vector Store:
    - library_missing
    - collection_not_found
    - embedding_store_empty
    - vector_store_connection_failed
    - healthy
    """
    # 1. Library Check
    try:
        import chromadb
        logger.debug("ChromaDB library imported successfully.")
    except ImportError:
        return {
            "status": "unhealthy",
            "error_type": "library_missing",
            "message": "ChromaDB library is not installed in the current environment.",
            "suggested_fix": "Run 'pip install chromadb' or check your virtual environment."
        }
    
    # 2. Persistence Path Check
    if not os.path.exists(Config.CHROMA_DB_PATH):
        return {
            "status": "unhealthy",
            "error_type": "vector_store_connection_failed",
            "message": f"Persistence directory missing: {Config.CHROMA_DB_PATH}",
            "suggested_fix": "Run bootstrap.py to build the vector store."
        }
    
    try:
        client = chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)
        collections = client.list_collections()
        col_names = [c.name for c in collections]
        
        target_col = f"{target_dataset}_documents"
        
        # 3. Collection Presence Check
        if target_col not in col_names:
            return {
                "status": "unhealthy",
                "error_type": "collection_not_found",
                "message": f"Target collection '{target_col}' not found in ChromaDB.",
                "suggested_fix": "Run bootstrap.py or pdf_chunker.py to ingest documents."
            }
        
        col = client.get_collection(target_col)
        count = col.count()
        
        # 4. Content Check
        if count == 0:
            return {
                "status": "degraded",
                "error_type": "embedding_store_empty",
                "message": f"Collection '{target_col}' exists but contains 0 embeddings.",
                "suggested_fix": "Run embedding_pipeline.py to process chunks."
            }
            
        # 5. Retrieval Integrity Check (Dummy Query)
        try:
            res = col.query(query_texts=["test"], n_results=1)
            retrieval_status = "verified" if res['ids'] else "failed"
        except Exception:
            retrieval_status = "failed"

        return {
            "status": "healthy",
            "collection": target_col,
            "embedding_count": count,
            "retrieval_verification": retrieval_status,
            "all_available_collections": col_names
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error_type": "vector_store_connection_failed",
            "message": f"Failed to connect to ChromaDB: {str(e)}",
            "suggested_fix": "Check permissions on the chroma directory or for stale lock files."
        }

def get_system_health(dataset: str = "vistastream") -> Dict[str, Any]:
    """
    Aggregates health checks for the entire backend stack with production-grade diagnostics.
    """
    db_path = Config.VISTASTREAM_DB_PATH if dataset == "vistastream" else Config.NEONPLAY_DB_PATH
    
    db_health = check_sqlite_health(db_path)
    chroma_health = check_chroma_health(dataset)
    
    # Overall Determination
    if db_health["status"] == "unhealthy" or chroma_health["status"] == "unhealthy":
        overall = "unhealthy"
    elif chroma_health["status"] == "degraded":
        overall = "degraded"
    else:
        overall = "healthy"
        
    return {
        "overall_status": overall,
        "dataset": dataset,
        "demo_mode": Config.DEMO_MODE,
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "database": db_health,
        "vector_store": chroma_health,
        "recommendation": "System is production-ready." if overall == "healthy" else "System requires manual intervention (see suggested_fix)."
    }

if __name__ == "__main__":
    print(json.dumps(get_system_health("vistastream"), indent=2))
    print("\n" + "-"*40 + "\n")
    print(json.dumps(get_system_health("neonplay"), indent=2))
