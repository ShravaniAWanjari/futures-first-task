"""
Module: validators.py
Purpose: Non-destructive data validation and schema integrity layer.
Responsibilities: Enforces numerical boundaries, date logic, unique ID integrity, and cross-table foreign key rules prior to ingestion.
Security Boundaries: Purely functional evaluation logic; makes absolutely zero database mutations.
Key Decisions: Differentiates validation strictness dynamically between the messy NeonPlay (Startup) and strict VistaStream (Enterprise) environments.
Inputs: Raw dictionary rows.
Outputs: Structured validation result payloads (`valid`, `severity`, `message`).
"""

from datetime import datetime

def make_result(valid, severity, message, action):
    """
    Creates a standardized structured validation result.
    action: accept | reject | normalize
    """
    return {
        "valid": valid,
        "severity": severity,
        "message": message,
        "action": action
    }

def validate_required_fields(row, required_columns):
    for col in required_columns:
        val = row.get(col)
        if val is None or str(val).strip() == "":
            return make_result(False, "ERROR", f"Missing critical field: {col}", "reject")
    return make_result(True, "INFO", "All required fields present", "accept")

def validate_date(date_str, dataset_type="startup", allow_empty=False):
    if not date_str or str(date_str).strip() == "":
        if allow_empty:
            return make_result(True, "INFO", "Empty date allowed", "accept")
        return make_result(False, "ERROR", "Missing date", "reject")
    
    date_str = str(date_str).strip()
    
    # Try ISO YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
    try:
        # Check standard ISO formatting
        if " " in date_str:
            datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        else:
            datetime.strptime(date_str, "%Y-%m-%d")
        return make_result(True, "INFO", "Valid ISO date", "accept")
    except ValueError:
        pass
        
    # Startup dataset can tolerate alternative formats by marking them for normalization
    if dataset_type == "startup":
        try:
            if " " in date_str:
                datetime.strptime(date_str, "%Y/%m/%d %H:%M:%S")
            else:
                datetime.strptime(date_str, "%Y/%m/%d")
            return make_result(False, "WARNING", f"Alternative date format detected: {date_str}", "normalize")
        except ValueError:
            pass
            
    return make_result(False, "ERROR", f"Unreadable date format: {date_str}", "reject")

def validate_numeric_range(value, min_val=None, max_val=None, allow_empty=False):
    if value is None or str(value).strip() == "" or str(value).strip().lower() == "nan":
        if allow_empty:
            return make_result(True, "INFO", "Empty numeric value allowed", "accept")
        return make_result(False, "ERROR", "Missing numeric value", "reject")
    
    try:
        num = float(value)
        if min_val is not None and num < min_val:
            return make_result(False, "ERROR", f"Value {num} below minimum {min_val}", "reject")
        if max_val is not None and num > max_val:
            # Phase 11: Stricter enforcement for startup spend outliers
            return make_result(False, "ERROR", f"Value {num} above maximum threshold {max_val}", "reject")
        return make_result(True, "INFO", "Valid numeric range", "accept")
    except ValueError:
        return make_result(False, "ERROR", f"Impossible numeric value: {value}", "reject")

def check_duplicate_pk(pk_value, pk_set):
    if not pk_value:
        return make_result(False, "ERROR", "Primary key is empty", "reject")
    if pk_value in pk_set:
        return make_result(False, "ERROR", f"Duplicate primary key detected: {pk_value}", "reject")
    return make_result(True, "INFO", "Unique PK", "accept")

def check_foreign_key(fk_value, valid_fk_set):
    if not fk_value:
        return make_result(False, "ERROR", "Missing foreign key", "reject")
    if valid_fk_set is not None and str(fk_value) not in valid_fk_set:
        return make_result(False, "ERROR", f"Invalid foreign key reference: {fk_value}", "reject")
    return make_result(True, "INFO", "Valid FK", "accept")

# --- Table Specific Validators ---

def validate_movie(row, seen_pks, dataset_type="startup"):
    req_res = validate_required_fields(row, ["movie_id", "title"])
    if not req_res["valid"]: return req_res
    
    pk_res = check_duplicate_pk(row["movie_id"], seen_pks)
    if not pk_res["valid"]: return pk_res
    
    if dataset_type == "enterprise":
        run_res = validate_numeric_range(row.get("runtime_minutes"), min_val=0, allow_empty=False)
        if not run_res["valid"]: return run_res
        
    seen_pks.add(row["movie_id"])
    return make_result(True, "INFO", "Movie row valid", "accept")

def validate_viewer(row, seen_pks, dataset_type="startup"):
    req_res = validate_required_fields(row, ["viewer_id", "region"])
    if not req_res["valid"]: return req_res
    
    pk_res = check_duplicate_pk(row["viewer_id"], seen_pks)
    if not pk_res["valid"]: return pk_res
    
    date_res = validate_date(row.get("join_date"), dataset_type, allow_empty=(dataset_type=="startup"))
    if not date_res["valid"]: return date_res
    
    seen_pks.add(row["viewer_id"])
    return make_result(True, "INFO", "Viewer row valid", "accept")

def validate_watch_activity(row, seen_pks, valid_viewers=None, valid_movies=None, dataset_type="startup"):
    req_res = validate_required_fields(row, ["activity_id", "viewer_id", "movie_id"])
    if not req_res["valid"]: return req_res
    
    pk_res = check_duplicate_pk(row["activity_id"], seen_pks)
    if not pk_res["valid"]: return pk_res
    
    fk1 = check_foreign_key(row["viewer_id"], valid_viewers)
    if not fk1["valid"]: return fk1
    
    fk2 = check_foreign_key(row["movie_id"], valid_movies)
    if not fk2["valid"]: return fk2
    
    comp_res = validate_numeric_range(row.get("completion_rate"), min_val=0, max_val=100, allow_empty=(dataset_type=="startup"))
    if not comp_res["valid"]: return comp_res
    
    mins_res = validate_numeric_range(row.get("watch_minutes"), min_val=0, allow_empty=(dataset_type=="startup"))
    if not mins_res["valid"]: return mins_res
    
    date_res = validate_date(row.get("watch_date"), dataset_type, allow_empty=False)
    if not date_res["valid"]: return date_res
    
    seen_pks.add(row["activity_id"])
    return make_result(True, "INFO", "Watch activity row valid", "accept")

def validate_review(row, seen_pks, valid_viewers=None, valid_movies=None, dataset_type="startup"):
    req_res = validate_required_fields(row, ["review_id", "viewer_id", "movie_id"])
    if not req_res["valid"]: return req_res
    
    pk_res = check_duplicate_pk(row["review_id"], seen_pks)
    if not pk_res["valid"]: return pk_res
    
    fk1 = check_foreign_key(row["viewer_id"], valid_viewers)
    if not fk1["valid"]: return fk1
    
    fk2 = check_foreign_key(row["movie_id"], valid_movies)
    if not fk2["valid"]: return fk2
    
    rating_res = validate_numeric_range(row.get("rating"), min_val=1, max_val=5, allow_empty=False)
    if not rating_res["valid"]: return rating_res
            
    date_res = validate_date(row.get("review_date"), dataset_type, allow_empty=(dataset_type=="startup"))
    if not date_res["valid"]: return date_res
    
    seen_pks.add(row["review_id"])
    return make_result(True, "INFO", "Review row valid", "accept")

def validate_campaign(row, seen_pks, dataset_type="startup"):
    # Phase 11: Region is now a mandatory analytical dimension
    required = ["campaign_id", "campaign_name", "region"]
    if dataset_type == "enterprise":
        required.append("quarter")
        
    req_res = validate_required_fields(row, required)
    if not req_res["valid"]: return req_res
    
    pk_res = check_duplicate_pk(row["campaign_id"], seen_pks)
    if not pk_res["valid"]: return pk_res
    
    # Cap startup spend at 10M to catch anomalies like CAM030
    max_spend = 10_000_000 if dataset_type == "startup" else 1_000_000_000
    spend_res = validate_numeric_range(row.get("spend_usd"), min_val=0, max_val=max_spend, allow_empty=(dataset_type=="startup"))
    if not spend_res["valid"]: return spend_res
    
    seen_pks.add(row["campaign_id"])
    return make_result(True, "INFO", "Campaign row valid", "accept")

def validate_regional_performance(row, dataset_type="startup"):
    # This table uses AUTOINCREMENT, so we don't have a PK to check here.
    req_res = validate_required_fields(row, ["region", "quarter"])
    if not req_res["valid"]: return req_res
    
    hours_res = validate_numeric_range(row.get("total_watch_hours"), min_val=0, allow_empty=(dataset_type=="startup"))
    if not hours_res["valid"]: return hours_res
    
    return make_result(True, "INFO", "Regional performance row valid", "accept")
