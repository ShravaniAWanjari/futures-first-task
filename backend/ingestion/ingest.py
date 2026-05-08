import argparse
import os
import sys
from backend.ingestion.csv_loader import run_ingestion
from backend.config import Config

def print_summary(summary, env_name):
    if summary.get("status") == "error":
        print(f"\n=== INGESTION SUMMARY ===")
        print(f"Environment: {env_name}")
        print(f"Status: FAILED")
        print(f"Error: {summary.get('message')}")
        return

    loaded = summary.get('rows_loaded', 0)
    rejected = summary.get('rows_rejected', 0)
    warnings = summary.get('warnings_count', 0)
    norms = summary.get('normalization_count', 0)
    
    if rejected > 0 and loaded > 0:
        status = "PARTIAL SUCCESS"
    elif rejected > 0 and loaded == 0:
        status = "FAILED"
    elif warnings > 0 or norms > 0:
        status = "SUCCESS WITH WARNINGS"
    else:
        status = "SUCCESS"

    print(f"\n=== INGESTION SUMMARY ===")
    print(f"Environment: {env_name}")
    print(f"Rows Loaded: {loaded:,}")
    print(f"Rows Rejected: {rejected:,}")
    print(f"Warnings: {warnings:,}")
    print(f"Normalizations: {norms:,}")
    print(f"\nStatus: {status}\n")

def run_env(env):
    if env == "enterprise":
        env_name = "VistaStream Global"
        db_path = Config.VISTASTREAM_DB_PATH
        data_dir = os.path.join(Config.BASE_DIR, "data", "enterprise_clean_data")
        dataset = "vistastream"
    elif env == "startup":
        env_name = "NeonPlay Media"
        db_path = Config.NEONPLAY_DB_PATH
        data_dir = os.path.join(Config.BASE_DIR, "data", "startup_messy_data")
        dataset = "neonplay"
    else:
        print(f"Unknown environment: {env}")
        return

    print(f"\nStarting ingestion for {env_name}...")
    print(f"Connecting to DB: {db_path}")
    print(f"Loading data from: {data_dir}")
    
    try:
        summary = run_ingestion(dataset, db_path, data_dir)
        print_summary(summary, env_name)
    except Exception as e:
        print(f"\n=== INGESTION CRASHED ===")
        print(f"Environment: {env_name}")
        print(f"Error: {str(e)}\n")
        # In a real system you'd probably raise, but we fail gracefully per requirements

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSV Ingestion Pipeline Runner")
    parser.add_argument("--env", choices=["enterprise", "startup", "both"], required=True, help="Environment to ingest data for")
    args = parser.parse_args()
    
    if args.env == "both":
        run_env("enterprise")
        run_env("startup")
    else:
        run_env(args.env)
