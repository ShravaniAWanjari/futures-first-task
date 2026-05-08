# Engineering Decisions & Tradeoffs

This document outlines the rationale behind the architectural stack and why specific tools were selected for this dual-environment streaming platform orchestration engine.

| Tool | Why Chosen | Why Not Alternatives |
|---|---|---|
| **SQLite** | Offers incredible operational simplicity, portability, and native relational querying. It is perfect for demonstrating robust schema design, primary/foreign key validations, and data normalization entirely within a deterministic flat-file system. | **PostgreSQL/MySQL**: Overkill for a local RAG orchestrator prototype. Requires external daemon management, network overhead, and complicates the reviewer's bootstrap process. |
| **ChromaDB** | Excellent, lightweight, open-source persistent vector store. Runs entirely locally and natively handles the dual-environment isolation pattern via discrete collections. Defaults to `all-MiniLM-L6-v2` locally which is exceptionally fast for testing. | **Pinecone / Weaviate**: Requires cloud API keys, network dependency, and introduces vendor lock-in that degrades the "one command bootstrap" experience. |
| **PyMuPDF (fitz)** | Extremely fast C-backed PDF parsing. Provides phenomenal control over text extraction layout block preservation natively, handling massive enterprise reports seamlessly. | **PyPDF2 / PDFMiner**: Much slower, heavily struggles with dynamic column layouts, and lacks PyMuPDF's resilience against corrupted export artifacts. |
| **Scratch-built Orchestrator** | Offers absolute control over the security boundaries. Every step (classification, extraction, chunking, routing, validation) is 100% transparent and deterministic. Ensures the LLM is explicitly firewalled from the raw DB using specific SQLite PRAGMAs. | **LangChain / LlamaIndex**: Highly opaque abstractions that introduce massive dependency bloat, unpredictability, and obscure execution traces. Building the orchestrator from scratch proves deep engineering comprehension. |
| **Sentence-Transformers** | Provides blazing-fast local embeddings that do not depend on external APIs, ensuring offline execution reliability and eliminating token latency constraints. | **OpenAI Embeddings**: Requires API tokens and generates recurring costs merely to verify pipeline integrity. |
| **Gemini / LLM Agnostic** | Standardizing the LLM injection as a modular tool ensures we aren't coupled to a specific vendor, allowing Gemini or any lightweight instruction-tuned model to drive the analytics later. | **Tight coupling to OpenAI**: Inhibits flexibility and introduces a hard dependency on single-provider API uptime. |

### Security & Deployment Philosophy
The core philosophy revolves around **Operational Predictability**. 
- The DB natively rejects DDL manipulations via `sql_guard.py` utilizing `EXPLAIN` verification and `PRAGMA query_only = ON;`.
- The deterministic bootstrapper (`bootstrap.py`) ensures that regardless of the initial environment configuration, a clean rebuild takes seconds, not hours.
