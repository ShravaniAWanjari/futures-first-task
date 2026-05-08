# Security Boundaries & Governance Architecture

This document outlines the strict access controls, data boundaries, and operational governance protocols implemented within the orchestration pipeline to guarantee secure, hallucination-resistant LLM integration.

## 1. LLM Access Philosophy
**The LLM never possesses direct access to the raw database or the unrestricted document store.**
- **What it can access**: Strictly bounded semantic document snippets (chunked via PyMuPDF) and strictly constrained structured database outputs (capped row arrays).
- **What it cannot access**: The raw SQLite DB files, the unchunked raw PDFs, the ingestion logs, and any execution environment state.

## 2. Validated SQL Guard Behavior (`sql_guard.py`)
To execute quantitative queries securely, we utilize a native SQLite firewall rather than relying on prompt engineering or basic string matching.
- **Whitelist Enforcement**: Only explicit tables (`movies`, `viewers`, etc.) and `SELECT`/`WITH` statements are permitted.
- **Native Syntax Defense**: We execute `EXPLAIN {query}` prior to running any logic. This forces the underlying SQLite engine to validate that the tables and columns physically exist, eliminating hallucinated columns gracefully.
- **Data Mutation Prevention**: The ultimate defense layer executes `PRAGMA query_only = ON;` on the execution connection, natively severing the ability for LLMs to run `DROP`, `DELETE`, `UPDATE`, or `INSERT` commands, regardless of bypass attempts.

## 3. Retrieval Restrictions (Chunk-Only Philosophy)
Rather than passing massive PDFs to an LLM, generating massive token costs and causing "lost-in-the-middle" context degradation:
- Documents are parsed into overlap-aware semantic chunks (500–900 characters).
- Only the highly relevant, similarity-matched chunks are passed to the context window via the retrieval layer.
- **Direct-Fetch Architecture**: The `retrieval_tools.py` directly interfaces with ChromaDB and outputs a sanitized string format. The orchestrator never acts as an unconstrained file reader.

## 4. Absolute Traceability Guarantees
Every piece of data served to the LLM maintains its provenance.
- **SQL Traceability**: Heuristic regex tagging maps every SQL query back to the exact tables queried.
- **Semantic Traceability**: Every PDF chunk is assigned a stable MD5 hash ID (`source_file` + `page_number` + `chunk_index`). This guarantees that every snippet can be definitively linked to the original document and page for citation checking.

## 5. Ingestion Governance
Data ingestion is highly divergent based on environmental readiness:
- **Enterprise (VistaStream)**: The system strictly expects perfect schemas and flawless validation. It operates on a "fail loud" methodology, rejecting unreadable schema violations immediately.
- **Startup (NeonPlay)**: Employs a proactive normalization protocol (`normalizers.py`) to systematically sanitize geographical strings (`Apac` -> `APAC`) and device tags without silently dropping data.

## 6. Ingestion Logging Philosophy
A transparent logging architecture is foundational for observability.
Every single ingestion event (successful insertion, duplicate PK rejection, validation warning, or text normalization) is dual-logged:
1. Flat file system logs (`logs/vistastream_ingestion.log`) for rapid DevOps debugging.
2. Relational SQLite table (`ingestion_logs`) for aggregable pipeline health monitoring.
