# 📝 Assumptions & Tradeoffs

## 🧐 Key Assumptions

1.  **Deterministic Routing vs. Pure RAG**: 
    - **Assumption**: Operational queries require high precision. 
    - **Implementation**: Instead of relying solely on an LLM to "decide" where to look, Iris uses a deterministic regex-based domain classifier first. This prevents the system from querying a database for a purely narrative question (like "What is the strategy?").

2.  **Dataset Separation**: 
    - **Assumption**: "VistaStream" and "NeonPlay" represent distinct organizational contexts.
    - **Implementation**: Ingestion and retrieval are strictly partitioned by workspace ID, ensuring data leakage does not occur between the "Clean Enterprise" and "Messy Startup" environments.

3.  **Local Embeddings**:
    - **Assumption**: Privacy and speed are prioritized for the initial retrieval phase.
    - **Implementation**: ChromaDB runs locally with `all-MiniLM-L6-v2` embeddings, eliminating the cost and latency of external API calls for the initial "needle-in-a-haystack" search.

---

## ⚖️ Tradeoffs & Design Decisions

### 1. SQLite for Session Persistence
- **Tradeoff**: SQLite was chosen over a heavier database like PostgreSQL.
- **Rationale**: For an operational intelligence prototype, SQLite provides zero-config persistence and sufficient performance for single-user analytical workflows. It allows the system to remain "clone-and-run" without requiring a separate database cluster.

### 2. Regex-Based Table Extraction
- **Tradeoff**: Using specialized regex patterns instead of LLM-based table parsing for narrative fragments.
- **Rationale**: While an LLM is better at general parsing, specialized regex patterns are 100% predictable and significantly faster. This ensures that critical financial data ($ spend, ROI) is consistently formatted into tables without hallucinations.

### 3. Synthesis Layer (Gemini)
- **Tradeoff**: Only using the LLM at the *end* of the pipeline (Synthesis) rather than the beginning (Routing).
- **Rationale**: This "Deterministic-Search-Generative-Synthesis" (DSGS) pattern ensures the LLM only sees verified evidence. It reduces the chance of "making up" metrics because the LLM is restricted to the technical context retrieved by the orchestrator.

### 4. Client-Side Layout Management
- **Tradeoff**: Managing the Source Panel state entirely in the frontend.
- **Rationale**: This allows for a snappy, reactive "instant one-click" experience when exploring data lineage. While a server-side state would allow for shared links, the current approach prioritizes the individual analyst's interactive speed.
