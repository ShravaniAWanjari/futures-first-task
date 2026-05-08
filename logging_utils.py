import os
import uuid
from datetime import datetime
import json
import logging

def get_file_logger(dataset):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"{dataset.lower()}_ingestion.log")
    
    logger = logging.getLogger(f"ingestion_{dataset}")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        try:
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception:
            pass  # Fail silently if file logger fails
            
    return logger

def log_ingestion_event(conn, dataset, source_file, table_name, row_reference, log_level, action_taken, message):
    log_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # 1. Write to DB
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ingestion_logs (log_id, dataset, source_file, table_name, row_reference, log_level, action_taken, message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (log_id, dataset, source_file, table_name, str(row_reference), log_level.upper(), action_taken, message, timestamp))
        conn.commit()
    except Exception as e:
        # DB logging failed, fallback to print or just ignore
        print(f"Failed to write to DB log: {e}")
        
    # 2. Write to File
    try:
        logger = get_file_logger(dataset)
        log_msg = f"[{source_file}] [{table_name}] [{row_reference}] [{action_taken}] {message}"
        if log_level.upper() == "INFO":
            logger.info(log_msg)
        elif log_level.upper() == "WARNING":
            logger.warning(log_msg)
        elif log_level.upper() == "ERROR":
            logger.error(log_msg)
    except Exception:
        pass # No crash if file logger fails
        
    return {
        "status": log_level.lower(),
        "action": action_taken,
        "message": message
    }

def log_info(conn, dataset, source_file, table_name, row_reference, action_taken, message):
    return log_ingestion_event(conn, dataset, source_file, table_name, row_reference, "INFO", action_taken, message)

def log_warning(conn, dataset, source_file, table_name, row_reference, action_taken, message):
    return log_ingestion_event(conn, dataset, source_file, table_name, row_reference, "WARNING", action_taken, message)

def log_error(conn, dataset, source_file, table_name, row_reference, action_taken, message):
    return log_ingestion_event(conn, dataset, source_file, table_name, row_reference, "ERROR", action_taken, message)

def generate_ingestion_summary(conn, dataset=None):
    """
    Returns a summary dictionary of ingestion stats.
    Includes: rows loaded, rows rejected, warnings count, normalization count, files processed.
    """
    try:
        cursor = conn.cursor()
        
        query_base = "SELECT action_taken, log_level, source_file FROM ingestion_logs"
        params = []
        if dataset:
            query_base += " WHERE dataset = ?"
            params.append(dataset)
            
        cursor.execute(query_base, params)
        rows = cursor.fetchall()
        
        rows_loaded = 0
        rows_rejected = 0
        warnings_count = 0
        normalization_count = 0
        files_processed = set()
        
        for action, level, source in rows:
            files_processed.add(source)
            if level == "INFO" and action in ["inserted", "loaded", "processed"]:
                rows_loaded += 1
            elif level == "ERROR":
                rows_rejected += 1
            elif level == "WARNING":
                warnings_count += 1
            if action == "normalized":
                normalization_count += 1
                
        return {
            "dataset": dataset or "All",
            "rows_loaded": rows_loaded,
            "rows_rejected": rows_rejected,
            "warnings_count": warnings_count,
            "normalization_count": normalization_count,
            "files_processed": len(files_processed)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate summary: {str(e)}"
        }
