import subprocess
import sys
import time
import os

def run_step(name, command):
    print(f"\n[{time.strftime('%H:%M:%S')}] === STAGE: {name} ===")
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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
    
    run_step("1. Constructing Databases & Initializing Schemas", "python create_databases.py")
    run_step("2. Executing Strict CSV Ingestion Pipeline", "python ingest.py --env both")
    run_step("3. Generating Database Ingestion Audits", "python verify_ingestion.py")
    run_step("4. Processing PDF Pipeline & Extracting Semantic Chunks", "python pdf_chunker.py")
    run_step("5. Building Local ChromaDB Embeddings", "python embedding_pipeline.py")
    run_step("6. Verifying End-to-End Retrieval Integrity", "python verify_retrieval.py")
    
    print("\n==========================================================")
    print("      SYSTEM BOOTSTRAP COMPLETE & FULLY OPERATIONAL       ")
    print("==========================================================")
    print("\nThe environment is pristine. You can safely execute the orchestration engine:")
    print(" -> python orchestrator.py\n")
