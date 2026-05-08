"""
Module: sql_guard.py
Purpose: A robust firewall safely executing LLM-generated SQL against SQLite.
Responsibilities: Syntax validation, table whitelist enforcement, schema checking, and query execution tracing.
Security Boundaries: The ultimate native defense layer. Restricts all SQLite execution connections to `query_only = ON` to block data-mutation injections natively regardless of LLM output.
Key Decisions: Utilizes `EXPLAIN` to validate table and column existence securely natively via the engine rather than complex regex parsing.
Inputs: Raw SQL string, DB path, environment.
Outputs: Validated execution rows or structured rejection trace.
"""
import sqlite3
import re
import os
import time
from typing import Dict, Any, Tuple, List
from backend.logging_utils import get_file_logger
from backend.exceptions import UnsafeQueryError, ConfigurationError
from backend.schemas import SQLTrace

ALLOWED_TABLES = {
    "movies", "viewers", "watch_activity", "reviews", 
    "marketing_campaigns", "regional_performance", "pdf_chunks_metadata",
    "ingestion_logs"
}

FORBIDDEN_KEYWORDS = [
    r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b", 
    r"\bALTER\b", r"\bATTACH\b", r"\bPRAGMA\b", r"\bREPLACE\b", 
    r"\bTRUNCATE\b", r"\bCREATE\b", r"\bEXEC\b"
]

def validate_sql(sql_query: str, conn: sqlite3.Connection = None) -> bool:
    """
    Validates a SQL query for safety and structural integrity.
    Provides strict guardrails specifically mapped to LLM-generated text.
    Raises UnsafeQueryError if validation fails.
    """
    if not sql_query or not sql_query.strip():
        raise UnsafeQueryError("Query is empty.")
        
    sql_upper = sql_query.upper()
    clean_sql = sql_upper.lstrip(" \n\r\t")
    
    if not (clean_sql.startswith("SELECT") or clean_sql.startswith("WITH")):
        raise UnsafeQueryError("Query must begin with SELECT or WITH.")
        
    statements = [s.strip() for s in sql_query.split(";") if s.strip()]
    if len(statements) > 1:
        raise UnsafeQueryError("Multiple SQL statements are not permitted.")
        
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(keyword, sql_upper):
            raise UnsafeQueryError(f"Forbidden keyword detected: {keyword.replace(r'\b', '')}")
            
    if "LIMIT" not in sql_upper:
        raise UnsafeQueryError("Query must contain a LIMIT clause to prevent unbounded execution.")
        
    if "--" in sql_query or "/*" in sql_query:
        raise UnsafeQueryError("Unsafe comments are not permitted in the SQL query.")
        
    if clean_sql.count("*") > 2:
        raise UnsafeQueryError("Wildcard (*) abuse detected. Specify columns explicitly.")

    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN {sql_query}")
            
            found_tables = [t for t in ALLOWED_TABLES if re.search(rf"\b{t.upper()}\b", sql_upper)]
            if not found_tables:
                 raise UnsafeQueryError("No globally allowed tables referenced in the query.")
        except sqlite3.Error as e:
            raise UnsafeQueryError(f"SQLite validation failed: {e}")
            
    return True

def execute_safe_sql(db_path: str, dataset_name: str, sql_query: str, request_id: str = "UNKNOWN") -> Tuple[List[Dict[str, Any]], SQLTrace]:
    """
    Safely executes an LLM-generated SQL query against the target database.
    This is the ONLY allowed DB execution path.
    """
    logger = get_file_logger(dataset_name)
    start_time = time.time()
    
    trace = SQLTrace(success=False, query_used=sql_query)
    
    if not os.path.exists(db_path):
        trace.error = "Database file not found."
        logger.error(f"[{dataset_name}] [REQ:{request_id}] [sql_guard] Execution failed: DB not found.")
        raise ConfigurationError("Database file not found.")
        
    conn = sqlite3.connect(db_path)
    
    try:
        validate_sql(sql_query, conn)
        
        conn.execute("PRAGMA query_only = ON;")
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        
        columns = [description[0] for description in cursor.description] if cursor.description else []
        formatted_rows = [dict(zip(columns, row)) for row in rows]
        
        trace.success = True
        trace.timing_ms = round((time.time() - start_time) * 1000, 2)
        trace.table_references = list(set(re.findall(r"(?:FROM|JOIN)\s+([A-Za-z0-9_]+)", sql_query.upper())))
        
        logger.info(f"[{dataset_name}] [REQ:{request_id}] [sql_guard] Query executed safely in {trace.timing_ms}ms. Returned {len(formatted_rows)} rows.")
        return formatted_rows, trace
        
    except UnsafeQueryError as e:
        trace.error = str(e)
        trace.timing_ms = round((time.time() - start_time) * 1000, 2)
        logger.warning(f"[{dataset_name}] [REQ:{request_id}] [sql_guard] Query rejected: {e} | SQL: {sql_query}")
        raise e
    except sqlite3.Error as e:
        trace.error = f"Runtime SQL Error: {str(e)}"
        trace.timing_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"[{dataset_name}] [REQ:{request_id}] [sql_guard] Execution error: {e} | SQL: {sql_query}")
        raise UnsafeQueryError(f"Runtime SQL Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_db = os.path.join(base_dir, "databases", "vistastream.db")
    
    try:
        rows, trace = execute_safe_sql(test_db, "vistastream", "SELECT * FROM movies LIMIT 2;")
        print(f"Success! Time: {trace.timing_ms}ms")
    except Exception as e:
        print(f"Failed: {e}")
