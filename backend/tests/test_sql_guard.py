"""Quick validation of SQL Guard hardening."""
from backend.orchestration.sql_guard import validate_sql
from backend.exceptions import UnsafeQueryError

# Should PASS
try:
    assert validate_sql("SELECT * FROM movies LIMIT 5") == True
    print("PASS: Valid query accepted")
except UnsafeQueryError as e:
    print(f"FAIL: Valid query rejected: {e}")

# Should BLOCK
blocked_queries = [
    ("UNION injection", "SELECT * FROM movies UNION ALL SELECT * FROM sqlite_master LIMIT 5"),
    ("sqlite_master direct", "SELECT * FROM sqlite_master LIMIT 5"),
    ("Unknown table", "SELECT * FROM secret_table LIMIT 5"),
    ("Recursive CTE", "WITH RECURSIVE cte AS (SELECT 1) SELECT * FROM cte LIMIT 5"),
    ("Multi-statement", "SELECT * FROM movies LIMIT 5; DROP TABLE movies;"),
]

for name, sql in blocked_queries:
    try:
        validate_sql(sql)
        print(f"FAIL: {name} was NOT blocked!")
    except UnsafeQueryError as e:
        print(f"PASS: {name} blocked -> {str(e)[:60]}")
