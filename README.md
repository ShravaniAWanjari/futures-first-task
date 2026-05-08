# Dual-Environment Streaming Analytics Platform

## Project Overview
This project establishes a comprehensive, secure, and fully observable ingestion and orchestration backend for a dual-environment streaming platform (VistaStream Global & NeonPlay Media). It dynamically parses operational data (CSVs) alongside unstructured policies (PDFs), bridging them securely for Retrieval-Augmented Generation (RAG) and Agentic Orchestration.

The architecture strictly delineates between **Enterprise** datasets (clean, strictly validated) and **Startup** datasets (messy, requiring automated normalization), offering a unified tooling layer that enforces LLM safety.

## Architecture Philosophy
- **Dual-Environment Validation**: Normalization scripts proactively correct noisy "startup" data, while Enterprise data fails-loudly on violations.
- **Absolute Security Boundaries**: The orchestration layer enforces `query_only = ON` in SQLite, actively preventing LLMs from initiating destructive mutations. The raw DB is entirely firewalled from external models.
- **Absolute Traceability**: Every SQL execution and semantic PDF chunk generates a deterministic hash ID mapping strictly back to the source document and page number.

## Core Component Flow
1. **Ingestion Engine (`ingest.py`)**: Filters incoming CSV rows through `validators.py` and `normalizers.py`, securely appending logs to the `ingestion_logs` table.
2. **Text Extraction (`pdf_chunker.py`)**: Uses PyMuPDF to extract layout-aware text, executing deterministic chunk overlaps and injecting the metadata back into the SQL database.
3. **Semantic Layer (`embedding_pipeline.py`)**: Ingests chunks into dedicated, environmentally isolated ChromaDB collections.
4. **Tool Access (`retrieval_tools.py`)**: Standardizes interfaces (`search_documents` and `query_structured_data`) that return strictly formatted strings, preventing context-window blowouts.
5. **Orchestrator (`orchestrator.py`)**: Resolves incoming queries via an NLP classifier, delegates to the appropriate retrieval tool, and constructs a completely sanitized response.

## Setup Instructions
To replicate the pristine state of this pipeline locally:

```bash
# 1. Clone & Set Up Environment
git clone <repository>
cd futures-first
python -m venv venv
source venv/bin/activate  # (or .\venv\Scripts\activate on Windows)

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Configure Env
cp .env.example .env
# Fill in GEMINI_API_KEY if testing live LLM generations later

# 4. Deterministic Bootstrap
python bootstrap.py
```

## Engineering Decisions & Tradeoffs
See `tool_decisions.md` for a comprehensive breakdown of why SQLite, ChromaDB, and a scratch-built orchestrator were chosen over heavyweight alternatives like LangChain or Postgres.

## Sample Execution
Test the orchestration system's multi-source reasoning directly:
```bash
python orchestrator.py
```
