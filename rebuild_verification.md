# Reproducibility & Rebuild Verification Guide

This project is built atop a deterministic, idempotent data pipeline. It guarantees that any engineer can clone the repository, run a single bootstrap script, and achieve a functionally identical pipeline state locally.

## 1. Fresh Environment Setup
To establish the baseline:
```bash
git clone <repository-url>
cd futures-first
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2. Deterministic Pipeline Bootstrap
Run the automated orchestrator to reconstruct the entire platform from zero:
```bash
python bootstrap.py
```

### Execution Pipeline & Runtime Expectations
The `bootstrap.py` script automatically triggers:
1. **Database Schema Initialization** (`create_databases.py`) - *Runtime: < 1s*
2. **Dual-Environment CSV Ingestion** (`ingest.py`) - *Runtime: ~20-60s* (Ingests 40,000+ rows and dual-logs to relational tables).
3. **Ingestion Quality Audit** (`verify_ingestion.py`) - *Runtime: < 2s*
4. **PDF Semantic Chunking** (`pdf_chunker.py`) - *Runtime: ~2-5s*
5. **ChromaDB Embedding Generation** (`embedding_pipeline.py`) - *Runtime: ~30s - 2m* (Note: Will automatically download the `all-MiniLM-L6-v2` weights on first execution).
6. **Retrieval Verification** (`verify_retrieval.py`) - *Runtime: < 2s*

## 3. System Health Verification Outputs
If the pipeline completed perfectly, you should observe the following outputs natively:
- **`verification_report.txt`**: Confirms row counts across both databases perfectly align with the expected clean/messy data constraints. Validates normalization frequencies and duplicate rejections explicitly.
- **`retrieval_verification_report.txt`**: Confirms that embeddings were generated, stored, and mapped back to the SQLite `pdf_chunks_metadata` successfully, and outputs the semantic query testing results proving that the vectors match the database.

## 4. End-to-End Orchestrator Test
Once bootstrapped, test the secure routing layer:
```bash
python orchestrator.py
```
**Expected Output**: The system should natively classify the provided test queries, route them to SQL/PDF abstractions accordingly, and output a clean JSON payload mapping strictly to `answer_context`, `sources`, and `trace`.

## 5. Common Troubleshooting
- **`ModuleNotFoundError` (`chromadb` / `pymupdf`)**: Ensure your virtual environment is properly activated before running the bootstrap pipeline.
- **Hanging on "Building Local ChromaDB Embeddings"**: Sentence-Transformers requires internet access strictly on the first initialization to pull the 90MB MiniLM embedding weights. Let it process.
- **SQLite Database Locks**: If a script crashed mid-execution, SQLite might retain a `database is locked` state. Simply delete the `databases/` directory and re-run `python bootstrap.py`.
