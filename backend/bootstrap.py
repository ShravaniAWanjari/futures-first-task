import subprocess
import sys
import time
import os
from pathlib import Path

def run_step(name, module_name, args=""):
    print(f"\n[{time.strftime('%H:%M:%S')}] === STAGE: {name} ===")
    cwd = str(Path(__file__).resolve().parent.parent)
    command = f'"{sys.executable}" -m {module_name} {args}'.strip()
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd)
        for line in process.stdout:
            print("  " + line.strip())
        process.wait()
        
        if process.returncode != 0:
            print(f"\n[ERROR] Stage '{name}' failed with code {process.returncode}.")
            print("Please fix the underlying errors and retry.")
            sys.exit(1)
        print(f"[SUCCESS] Stage '{name}' completed gracefully.")
        
    except KeyboardInterrupt:
        print("\n[FATAL] Bootstrap interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL] Exception occurred during '{name}': {e}")
        sys.exit(1)

def validate_environment_precheck():
    """Ensure basic requirements before running anything."""
    print(f"[{time.strftime('%H:%M:%S')}] Validating environment...")
    
    try:
        import dotenv
    except ImportError:
        print("[ERROR] python-dotenv is not installed. Please install dependencies.")
        sys.exit(1)
        
    if not Path(".env").exists():
        print("[WARNING] .env file not found. Falling back to environment variables.")
        
    print("[SUCCESS] Environment precheck passed.")

if __name__ == "__main__":
    print("==========================================================")
    print("  VISTASTREAM & NEONPLAY DETERMINISTIC BOOTSTRAP MANAGER  ")
    print("==========================================================")
    print("This pipeline will wipe and rebuild the entire data system from scratch.")
    
    validate_environment_precheck()
    
    # We run these modules directly from project root, safely
    run_step("1. Constructing Databases & Initializing Schemas", "backend.create_databases")
    run_step("2. Executing Strict CSV Ingestion Pipeline", "backend.ingestion.ingest", "--env both")
    run_step("3. Generating Database Ingestion Audits", "backend.verification.verify_ingestion")
    run_step("4. Processing PDF Pipeline & Extracting Semantic Chunks", "backend.ingestion.pdf_chunker")
    run_step("5. Building Local ChromaDB Embeddings", "backend.ingestion.embedding_pipeline")
    run_step("6. Verifying End-to-End Retrieval Integrity", "backend.verification.verify_retrieval")
    
    print("\n==========================================================")
    print("      SYSTEM BOOTSTRAP COMPLETE & FULLY OPERATIONAL       ")
    print("==========================================================")
    print("\nThe environment is pristine. You can safely execute the orchestration engine:")
    print(f" -> {sys.executable} -m backend.api.app\n")
