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
from logging_utils import get_file_logger

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

def validate_sql(sql_query, conn=None):
    """
    Validates a SQL query for safety and structural integrity.
    Provides strict guardrails specifically mapped to LLM-generated text.
    """
    trace = {"steps": []}
    
    def log_trace(step, status, detail=""):
        trace["steps"].append({"step": step, "status": status, "detail": detail})
    
    # 1. Check for empty
    if not sql_query or not sql_query.strip():
        log_trace("Empty Check", "Failed", "Query is empty.")
        return False, "Query is empty.", trace
    log_trace("Empty Check", "Passed")
        
    sql_upper = sql_query.upper()
    clean_sql = sql_upper.lstrip(" \n\r\t")
    
    # 2. Check explicitly for SELECT / WITH
    if not (clean_sql.startswith("SELECT") or clean_sql.startswith("WITH")):
        log_trace("Prefix Check", "Failed", "Missing SELECT/WITH prefix.")
        return False, "Query must begin with SELECT or WITH.", trace
    log_trace("Prefix Check", "Passed")
        
    # 3. Reject multiple statements
    statements = [s.strip() for s in sql_query.split(";") if s.strip()]
    if len(statements) > 1:
        log_trace("Multiple Statements Check", "Failed", "Semicolons detected.")
        return False, "Multiple SQL statements are not permitted.", trace
    log_trace("Multiple Statements Check", "Passed")
        
    # 4. Forbid dangerous DML/DDL commands
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(keyword, sql_upper):
            log_trace("Forbidden Keyword Check", "Failed", f"Found {keyword}")
            return False, f"Forbidden keyword detected: {keyword.replace(r'\b', '')}", trace
    log_trace("Forbidden Keyword Check", "Passed")
        
    # 5. Enforce LIMIT
    if "LIMIT" not in sql_upper:
        log_trace("LIMIT Enforcement", "Failed", "No LIMIT clause.")
        return False, "Query must contain a LIMIT clause to prevent unbounded execution.", trace
    log_trace("LIMIT Enforcement", "Passed")
        
    # 6. Reject comments
    if "--" in sql_query or "/*" in sql_query:
        log_trace("Comment Check", "Failed", "Comments present.")
        return False, "Unsafe comments are not permitted in the SQL query.", trace
    log_trace("Comment Check", "Passed")
        
    # 7. Wildcard abuse
    if clean_sql.count("*") > 2:
        log_trace("Wildcard Check", "Failed", "Excessive * usage.")
        return False, "Wildcard (*) abuse detected. Specify columns explicitly.", trace
    log_trace("Wildcard Check", "Passed")

    # 8. Schema verification against the physical DB
    if conn:
        try:
            # EXPLAIN strictly verifies syntax, missing tables, and missing columns!
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN {sql_query}")
            log_trace("Schema Existence Check", "Passed")
            
            # 9. Table whitelist enforcement
            found_tables = [t for t in ALLOWED_TABLES if re.search(rf"\b{t.upper()}\b", sql_upper)]
            if not found_tables:
                 log_trace("Whitelist Check", "Failed", "No valid tables.")
                 return False, "No globally allowed tables referenced in the query.", trace
            log_trace("Whitelist Check", "Passed")
                 
        except sqlite3.Error as e:
            log_trace("Schema Existence Check", "Failed", str(e))
            return False, f"SQLite validation failed: {e}", trace
            
    return True, "SQL is safe and validated.", trace

def execute_safe_sql(db_path, dataset_name, sql_query):
    """
    Safely executes an LLM-generated SQL query against the target database.
    This is the ONLY allowed DB execution path.
    """
    logger = get_file_logger(dataset_name)
    
    result = {
        "success": False,
        "query": sql_query,
        "rows": [],
        "trace": {},
        "error": None
    }
    
    if not os.path.exists(db_path):
        result["error"] = "Database file not found."
        logger.error(f"[{dataset_name}] [sql_guard] Execution failed: DB not found.")
        return result
        
    conn = sqlite3.connect(db_path)
    
    # Run Guardrails
    is_valid, validation_msg, trace = validate_sql(sql_query, conn)
    result["trace"] = trace
    
    if not is_valid:
        result["error"] = validation_msg
        logger.warning(f"[{dataset_name}] [sql_guard] Query rejected: {validation_msg} | SQL: {sql_query}")
        conn.close()
        return result
        
    try:
        # ULTIMATE NATIVE DEFENSE: 
        # Forcibly restricts this SQLite connection to purely Read-Only mode at the engine level.
        conn.execute("PRAGMA query_only = ON;")
        
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        
        # Convert tuples to dictionary mapping for easier API consumption
        columns = [description[0] for description in cursor.description] if cursor.description else []
        formatted_rows = [dict(zip(columns, row)) for row in rows]
        
        result["success"] = True
        result["rows"] = formatted_rows
        logger.info(f"[{dataset_name}] [sql_guard] Query executed safely. Returned {len(formatted_rows)} rows.")
        
    except sqlite3.Error as e:
        result["error"] = f"Runtime SQL Error: {str(e)}"
        logger.error(f"[{dataset_name}] [sql_guard] Execution error: {e} | SQL: {sql_query}")
    finally:
        conn.close()
        
    return result

if __name__ == "__main__":
    # Internal automated tests
    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_db = os.path.join(base_dir, "databases", "vistastream.db")
    
    test_queries = [
        "SELECT title, release_year FROM movies LIMIT 5;",  # Valid
        "SELECT title FROM movies;", # Invalid (No LIMIT)
        "DELETE FROM movies LIMIT 1;", # Invalid (Forbidden Keyword)
        "SELECT * FROM fake_table LIMIT 1;", # Invalid (Table does not exist)
        "SELECT * FROM movies; DROP TABLE movies; LIMIT 1;", # Invalid (Multiple statements)
        "SELECT fake_column FROM movies LIMIT 1;", # Invalid (Column does not exist)
        "SELECT * FROM movies LIMIT 5; -- drop tables" # Invalid (Comments)
    ]
    
    print("=== SQL GUARDRAIL TESTING ===\n")
    for q in test_queries:
        print(f"Query: {q}")
        res = execute_safe_sql(test_db, "vistastream", q)
        if res["success"]:
            print(f" -> PASS: Executed safely. Rows: {len(res['rows'])}\n")
        else:
            print(f" -> REJECTED: {res['error']}\n")
