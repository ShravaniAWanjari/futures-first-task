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

## Operational Observability
The platform includes a dedicated health monitoring system to ensure retrieval and ingestion integrity.

### Health Snapshot System
To verify the system's operational readiness, run:
```bash
python -m backend.system_health
```

### Operational States
The health system categorizes the vector store into explicit states:
- **`healthy`**: Collections found, embeddings exist, and retrieval is verified.
- **`degraded`**: Collections exist but are empty (requires embedding rebuild).
- **`unhealthy`**: Missing libraries, connection failures, or missing collections.

### Understanding Warning Counts
The **NeonPlay (Startup)** environment intentionally reports high warning and normalization counts (e.g., ~40,000). This reflects the platform's ability to handle and correct "messy" real-world startup data at scale without failing the pipeline.

## Demo Mode
For interviews and presentations, the system supports a `DEMO_MODE=true` environment flag. This enables:
- **Stability**: Returns deterministic examples for common queries.
- **Speed**: Limits retrieval counts (top 2 results) to prevent response lag.
- **Safety**: Injects a demo-marker into all response payloads.

## Engineering Decisions & Tradeoffs
See `docs/engineering/tool_decisions.md` for a comprehensive breakdown of why SQLite, ChromaDB, and a scratch-built orchestrator were chosen.

## Quality Assurance
The backend is verified by a robust test suite and audit reports:
- **Logic Verification**: `pytest`
- **Ingestion Audit**: `backend/verification/verify_ingestion.py`
- **Retrieval Audit**: `backend/verification/verify_retrieval.py`

### Retrieval Quality Validation
We implement a lightweight semantic sanity-check layer to ensure retrieval accuracy against deterministic management queries. This layer validates:
- **Source Grounding**: Checks if the expected PDF source is present in the top-k results.
- **Keyword Overlap**: Verifies that critical semantic tokens are present in the retrieved chunks.
- **Topic Consistency**: Heuristic validation of topical relevance.

**Sample Validation Output:**
```text
Query: APAC growth contribution
Status: [PASS] Expected source found in top retrievals with strong keyword overlap.
Retrieved Sources: Q2 FY2026 Campaign Performance Summary.pdf
Keyword Overlap: 3
```
This ensures that the semantic engine remains reliable without the overhead of complex ML benchmarking infrastructure.
