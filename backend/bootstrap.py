import subprocess
import sys
import time
import os

def run_step(name, script_name, args=""):
    print(f"\n[{time.strftime('%H:%M:%S')}] === STAGE: {name} ===")
    # Use sys.executable to ensure we use the same virtual environment
    # Run from the project root (parent of backend/)
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    command = f'"{sys.executable}" {script_name} {args}'
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

if __name__ == "__main__":
    print("==========================================================")
    print("  VISTASTREAM & NEONPLAY DETERMINISTIC BOOTSTRAP MANAGER  ")
    print("==========================================================")
    print("This pipeline will wipe and rebuild the entire data system from scratch.")
    time.sleep(1)
    
    run_step("1. Constructing Databases & Initializing Schemas", "backend/create_databases.py")
    # Using module execution to satisfy absolute imports
    run_step("2. Executing Strict CSV Ingestion Pipeline", "-m backend.ingestion.ingest", "--env both")
    run_step("3. Generating Database Ingestion Audits", "-m backend.verification.verify_ingestion")
    run_step("4. Processing PDF Pipeline & Extracting Semantic Chunks", "-m backend.ingestion.pdf_chunker")
    run_step("5. Building Local ChromaDB Embeddings", "-m backend.ingestion.embedding_pipeline")
    run_step("6. Verifying End-to-End Retrieval Integrity", "-m backend.verification.verify_retrieval")
    
    print("\n==========================================================")
    print("      SYSTEM BOOTSTRAP COMPLETE & FULLY OPERATIONAL       ")
    print("==========================================================")
    print("\nThe environment is pristine. You can safely execute the orchestration engine:")
    print(f" -> {sys.executable} orchestrator.py\n")
