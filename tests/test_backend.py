import pytest
from backend.orchestration.query_classifier import classify_query
from backend.orchestration.sql_guard import validate_sql
from backend.ingestion.normalizers import normalize_region
from backend.ingestion.validators import validate_watch_activity
from backend.exceptions import UnsafeQueryError

# --- Query Classifier Tests ---

def test_query_classifier_sql_intent():
    res = classify_query("What is the average completion rate for top 10 movies?")
    assert res["query_type"] == "sql"
    assert "query_structured_data" in res["recommended_tools"]

def test_query_classifier_pdf_intent():
    res = classify_query("What is the official executive policy on data handling?")
    assert res["query_type"] == "pdf"
    assert "search_documents" in res["recommended_tools"]

def test_query_classifier_hybrid_intent():
    res = classify_query("Why did revenue drop in Q2? Does the executive report explain it?")
    assert res["query_type"] == "hybrid"
    assert "search_documents" in res["recommended_tools"]
    assert "query_structured_data" in res["recommended_tools"]

# --- SQL Guard Tests ---

def test_sql_guard_rejects_missing_limit():
    with pytest.raises(UnsafeQueryError, match="LIMIT"):
        validate_sql("SELECT * FROM movies;")

def test_sql_guard_rejects_destructive_dml():
    # Prefix check happens first, but it still raises UnsafeQueryError
    with pytest.raises(UnsafeQueryError):
        validate_sql("DELETE FROM movies LIMIT 1;")

def test_sql_guard_rejects_forbidden_keyword_in_ctes():
    # Using a CTE to bypass prefix check but still containing a forbidden keyword
    with pytest.raises(UnsafeQueryError, match="Forbidden keyword"):
        validate_sql("WITH data AS (SELECT * FROM movies) DELETE FROM movies WHERE id IN (SELECT id FROM data) LIMIT 1;")

def test_sql_guard_rejects_multiple_statements():
    with pytest.raises(UnsafeQueryError, match="Multiple SQL statements"):
        validate_sql("SELECT * FROM movies LIMIT 1; DROP TABLE viewers;")

def test_sql_guard_rejects_unsafe_comments_via_multi_statement():
    # Comments with semicolon trigger multiple statement check
    with pytest.raises(UnsafeQueryError, match="Multiple SQL statements"):
        validate_sql("SELECT * FROM movies LIMIT 1; -- malicious code")

def test_sql_guard_accepts_clean_query():
    assert validate_sql("SELECT title, release_year FROM movies LIMIT 5;") is True

# --- Normalizer Tests ---

def test_region_normalization_startup_data():
    res = normalize_region("Apac", dataset_type="startup")
    assert res["value"] == "APAC"
    assert res["changed"] is True

def test_region_normalization_enterprise_passthrough():
    res = normalize_region("Apac", dataset_type="enterprise")
    # Enterprise should NOT normalize mapping, only whitespace
    assert res["value"] == "Apac"
    assert res["changed"] is False

# --- Validator Tests ---

def test_invalid_completion_rate_rejected():
    row = {"activity_id": "1", "viewer_id": "1", "movie_id": "1", "watch_minutes": "10", "completion_rate": "150", "watch_date": "2026-05-08"}
    seen_pks = set()
    res = validate_watch_activity(row, seen_pks, dataset_type="startup")
    assert res["valid"] is False
    assert "above maximum 100" in res["message"]

def test_negative_watch_minutes_rejected():
    row = {"activity_id": "1", "viewer_id": "1", "movie_id": "1", "watch_minutes": "-5", "completion_rate": "50", "watch_date": "2026-05-08"}
    seen_pks = set()
    res = validate_watch_activity(row, seen_pks, dataset_type="startup")
    assert res["valid"] is False
    assert "below minimum 0" in res["message"]
