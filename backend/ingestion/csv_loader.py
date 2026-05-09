"""
Module: csv_loader.py
Purpose: Modular CSV ingestion engine loading raw operational files into structured SQLite databases.
Responsibilities: Handles transaction rolling, normalization routing, and validation mapping during table loading.
Security Boundaries: Enforces isolated datasets; guarantees no silent failures on invalid primary keys.
Key Decisions: Implemented purely row-by-row state evaluation to provide meticulous error log traceability instead of batch-failing.
Inputs: CSV paths, database connection, duplicate-checking state sets.
Outputs: Standardized database rows and structured metric summaries.
"""

import pandas as pd
import sqlite3
import os
from backend.logging_utils import log_info, log_warning, log_error, generate_ingestion_summary
from backend.ingestion import normalizers
from backend.ingestion import validators

def handle_nan(val):
    if pd.isna(val) or val == "":
        return None
    return val

def normalize_text_only(value, dataset_type="startup"):
    cleaned = normalizers.normalize_text_field(value)
    if cleaned != value:
        return {"value": cleaned, "changed": True, "message": f"Trimmed whitespace: '{value}' -> '{cleaned}'"}
    return {"value": value, "changed": False, "message": None}

def load_csv_safe(csv_path, dataset_type):
    try:
        # Phase 11: Explicitly disable NA filtering to prevent 'NA' (North America) from being treated as null
        return pd.read_csv(csv_path, keep_default_na=False, na_filter=False)
    except Exception as e:
        if dataset_type == "enterprise":
            raise RuntimeError(f"Failed to load CSV {csv_path}: {e}")
        else:
            print(f"WARNING: Skipping unreadable CSV {csv_path} for startup dataset.")
            return None

def _process_table(conn, dataset, csv_path, table_name, expected_cols, normalizer_map, validator_func, pk_col, extra_val_args=None):
    dataset_type = "enterprise" if "vistastream" in dataset.lower() else "startup"
    df = load_csv_safe(csv_path, dataset_type)
    if df is None: return
    
    if dataset_type == "enterprise":
        missing_cols = [c for c in expected_cols if c not in df.columns]
        if missing_cols:
            log_error(conn, dataset, csv_path, table_name, "schema", "rejected", f"Enterprise schema mismatch. Missing: {missing_cols}")
            raise ValueError(f"Enterprise schema mismatch in {table_name}. Missing columns: {missing_cols}")
            
    rows_to_insert = []
    if extra_val_args is None:
        extra_val_args = {}
        
    for idx, row_series in df.iterrows():
        row = {k: handle_nan(v) for k, v in row_series.items()}
        row_ref = row.get(pk_col) if pk_col else f"row_{idx}"
        if not row_ref:
            row_ref = f"row_{idx}"
            
        # 1. Normalize
        for field, norm_func in normalizer_map.items():
            if field in row:
                row[field] = normalizers.process_and_log_normalization(
                    conn, dataset, csv_path, table_name, row_ref, field, row[field], norm_func
                )
                
        # 2. Validate
        val_result = validator_func(row, dataset_type=dataset_type, **extra_val_args)
        
        # 3. Handle Result
        if val_result["valid"]:
            if val_result["severity"] == "WARNING":
                log_warning(conn, dataset, csv_path, table_name, row_ref, "validation_warning", val_result["message"])
                
            rows_to_insert.append(tuple(row.get(col) for col in expected_cols))
            log_info(conn, dataset, csv_path, table_name, row_ref, "inserted", "Row loaded successfully")
        else:
            log_error(conn, dataset, csv_path, table_name, row_ref, "rejected", val_result["message"])
            
    # 4. Transactional Insert
    if rows_to_insert:
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            placeholders = ",".join(["?"] * len(expected_cols))
            cursor.executemany(f"INSERT INTO {table_name} ({','.join(expected_cols)}) VALUES ({placeholders})", rows_to_insert)
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            log_error(conn, dataset, csv_path, table_name, "batch", "rejected", f"Transaction failed: {e}")

# --- Table Loaders ---

def load_movies(conn, dataset, csv_path, seen_pks):
    normalizer_map = {
        "title": normalize_text_only,
        "genre": normalizers.normalize_genre
    }
    _process_table(
        conn, dataset, csv_path, "movies",
        ["movie_id", "title", "genre", "release_year", "language", "content_rating", "runtime_minutes"],
        normalizer_map, validators.validate_movie, "movie_id", {"seen_pks": seen_pks}
    )

def load_viewers(conn, dataset, csv_path, seen_pks):
    normalizer_map = {
        "region": normalizers.normalize_region,
        "device_type": normalizers.normalize_device_type,
        "subscription_type": normalizers.normalize_subscription_type
    }
    _process_table(
        conn, dataset, csv_path, "viewers",
        ["viewer_id", "region", "country", "age_group", "subscription_type", "device_type", "join_date"],
        normalizer_map, validators.validate_viewer, "viewer_id", {"seen_pks": seen_pks}
    )

def load_watch_activity(conn, dataset, csv_path, seen_pks, valid_viewers, valid_movies):
    normalizer_map = {
        "device_used": normalizers.normalize_device_type
    }
    _process_table(
        conn, dataset, csv_path, "watch_activity",
        ["activity_id", "viewer_id", "movie_id", "watch_date", "watch_minutes", "completion_rate", "device_used"],
        normalizer_map, validators.validate_watch_activity, "activity_id", 
        {"seen_pks": seen_pks, "valid_viewers": valid_viewers, "valid_movies": valid_movies}
    )

def load_reviews(conn, dataset, csv_path, seen_pks, valid_viewers, valid_movies):
    normalizer_map = {
        "review_text": normalize_text_only,
        "sentiment": normalize_text_only
    }
    _process_table(
        conn, dataset, csv_path, "reviews",
        ["review_id", "viewer_id", "movie_id", "rating", "review_text", "sentiment", "review_date"],
        normalizer_map, validators.validate_review, "review_id", 
        {"seen_pks": seen_pks, "valid_viewers": valid_viewers, "valid_movies": valid_movies}
    )

def load_campaigns(conn, dataset, csv_path, seen_pks):
    normalizer_map = {
        "region": normalizers.normalize_region,
        "campaign_name": normalize_text_only,
        "platform": normalize_text_only
    }
    _process_table(
        conn, dataset, csv_path, "marketing_campaigns",
        ["campaign_id", "campaign_name", "region", "platform", "spend_usd", "impressions", "conversion_rate", "quarter"],
        normalizer_map, validators.validate_campaign, "campaign_id", {"seen_pks": seen_pks}
    )

def load_regional_performance(conn, dataset, csv_path):
    normalizer_map = {
        "region": normalizers.normalize_region
    }
    _process_table(
        conn, dataset, csv_path, "regional_performance",
        ["region", "quarter", "total_watch_hours", "new_subscribers", "churn_rate", "avg_completion_rate"],
        normalizer_map, validators.validate_regional_performance, None, {}
    )

def run_ingestion(dataset_name, db_path, data_dir):
    """
    Main ingestion orchestrator.
    Returns structured ingestion summary.
    """
    if not os.path.exists(db_path):
        return {"status": "error", "message": f"Database {db_path} not found."}
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    seen_movies = set()
    seen_viewers = set()
    seen_activities = set()
    seen_reviews = set()
    seen_campaigns = set()
    
    # Must run sequentially to preserve foreign key integrity logic
    if os.path.exists(os.path.join(data_dir, "movies.csv")):
        print(" -> Processing movies.csv...")
        load_movies(conn, dataset_name, os.path.join(data_dir, "movies.csv"), seen_movies)
        
    if os.path.exists(os.path.join(data_dir, "viewers.csv")):
        print(" -> Processing viewers.csv...")
        load_viewers(conn, dataset_name, os.path.join(data_dir, "viewers.csv"), seen_viewers)
        
    if os.path.exists(os.path.join(data_dir, "watch_activity.csv")):
        print(" -> Processing watch_activity.csv...")
        load_watch_activity(conn, dataset_name, os.path.join(data_dir, "watch_activity.csv"), seen_activities, seen_viewers, seen_movies)
        
    if os.path.exists(os.path.join(data_dir, "reviews.csv")):
        print(" -> Processing reviews.csv...")
        load_reviews(conn, dataset_name, os.path.join(data_dir, "reviews.csv"), seen_reviews, seen_viewers, seen_movies)
        
    # Some tables use different filenames in our generation script
    marketing_file = os.path.join(data_dir, "marketing_spend.csv")
    if os.path.exists(marketing_file):
        print(" -> Processing marketing_spend.csv...")
        load_campaigns(conn, dataset_name, marketing_file, seen_campaigns)
        
    if os.path.exists(os.path.join(data_dir, "regional_performance.csv")):
        print(" -> Processing regional_performance.csv...")
        load_regional_performance(conn, dataset_name, os.path.join(data_dir, "regional_performance.csv"))
        
    summary = generate_ingestion_summary(conn, dataset_name)
    conn.close()
    
    return summary
