# Backend Security + Operational Hardening — Implementation Log

## Status: ALL PHASES IMPLEMENTED ✅

---

## Part 1: Security & Robustness

### Phase 1 — SQL Validation Hardening ✅
**File:** `backend/orchestration/sql_guard.py`
- Replaced positive-match validation with **full table extraction**
- Added `_extract_all_tables()` — parses ALL FROM/JOIN references
- Every referenced table is now validated against whitelist
- Added explicit **denylist**: `sqlite_master`, `sqlite_schema`, `information_schema`
- Blocks: `UNION`, `DETACH`, `VACUUM`, `REINDEX`, recursive CTEs
- **Test:** All 5 injection patterns blocked (verified via `test_sql_guard.py`)

### Phase 2 — Metadata Leakage Removal ✅
**File:** `backend/orchestration/retrieval_tools.py`
- Removed `Trace ID: {chunk_id}` from `format_document_results`
- Stripped `chunk_id` from source references in `orchestrator.py`
- Frontend now only receives: source title, section, page, excerpt

### Phase 3 — Session Isolation Hardening ✅
**File:** `backend/api/session_manager.py`, `session_service.py`, `app.py`
- Sessions now generate a `session_secret` (via `secrets.token_urlsafe(32)`)
- Added `validate_session_secret()` for ownership checks
- `create_session` returns `{session_id, session_secret}`
- Legacy sessions (no secret) remain accessible for backward compat

### Phase 4 — Synthesis Token Safety ✅
**File:** `backend/api/services/response_synthesizer.py`
- Added `MAX_SNIPPET_CHARS = 500` — truncates oversized chunks
- Added `MAX_FINDINGS = 4` — caps total findings per response
- Truncation preserves sentence boundaries (splits on last period)
- Eliminates token overflow and latency spikes

### Phase 5 — Entity False Negative Fix ✅
**File:** `backend/orchestration/retrieval_tools.py`
- Added `ENTITY_ALIASES` map: APAC↔Asia Pacific, LATAM↔Latin America, EMEA↔Europe/Middle East/Africa, NA↔North America/US/Canada
- Added `_expand_entity_aliases()` for multi-variant matching
- **Changed from hard-filter to soft penalty**: non-matching entities reduce confidence by 30% instead of hard rejection
- Chunks are only dropped if penalty pushes confidence below 0.15

### Phase 6 — Context Stickiness Fix ✅
**File:** `backend/orchestration/query_classifier.py`, `orchestrator.py`
- Conversational actions (formatting, clarification, continuation, refinement) now feed into follow-up detection
- Context memory window built from last 6 messages
- Follow-ups only inherit from recent assistant responses, not arbitrary history

---

## Part 2: Conversational UX

### Phase 7 — Small Talk Layer ✅
**File:** `backend/orchestration/query_classifier.py`, `orchestrator.py`
- Added `_is_small_talk()` — detects greetings, acknowledgements, capability questions, farewells
- `SMALL_TALK_RESPONSES` dict with formatted, helpful responses
- Small talk queries return `query_type: "conversational"` — **never trigger retrieval**
- Orchestrator handles early return for conversational type

### Phase 8 — Response Tone Modes ✅
**File:** `backend/api/services/response_synthesizer.py`
- Added `_detect_tone()` — detects: concise, conversational, executive, standard
- Concise tone → bullet-only output (200 char max per point)
- Executive tone → full structured report with headers
- Standard → balanced formatting with `### Key Findings` headers
- Tone adapts without changing factual grounding

### Phase 9 — Domain Gating Softened ✅
**File:** `backend/orchestration/query_classifier.py`
- Changed restriction regex from `write|generate|create + ANY WORD` to `write|generate|create + CODE-SPECIFIC TARGET`
- "create a summary" → ✅ Allowed
- "create python code" → ❌ Blocked
- Added optional `a/an` support in regex for natural phrasing

---

## Part 3: Response Synthesis & Memory

### Conversational Action Classification ✅
**File:** `backend/orchestration/query_classifier.py`
- Added `_classify_conversational_action()` — detects:
  - `formatting_request` (e.g., "use bullet points")
  - `clarification_request` (e.g., "what do you mean by X")
  - `continuation_request` (e.g., "continue", "go on")
  - `refinement_request` (e.g., "shorter version", "executive summary")
- These actions automatically trigger follow-up behavior

### Context Memory Window ✅
**File:** `backend/orchestration/orchestrator.py`
- Builds `context_memory` from last assistant response in recent 6 messages
- Clarification and follow-up queries reuse memory before fresh retrieval
- Empty-response fallback now tries memory context first

### Executive Response Structuring ✅
**File:** `backend/api/services/response_synthesizer.py`
- Responses now use `### Key Findings` and `### Additional Context` markdown headers
- Bullet points use `\n- ` format (standard markdown)
- Headers ending in colon are auto-bolded and newline-separated
- Excessive newlines collapsed to max 2

### Reduced Empty Failures ✅
**File:** `backend/orchestration/orchestrator.py`
- Low-confidence failure message now provides helpful rephrasing guidance
- Follow-up queries that find no new data fall back to context memory
- "No evidence found" only appears when both memory AND retrieval are empty

### Schema Updates ✅
**File:** `backend/schemas.py`
- `ClassificationTrace` extended with: `conversational_response`, `conversational_action`, `follow_up_detected`, `resolved_query`, `operational_domain`

---

## Files Modified

| File | Changes |
|------|---------|
| `sql_guard.py` | Full table validation, denylist, UNION/CTE blocking |
| `retrieval_tools.py` | Metadata stripping, entity aliases, soft matching |
| `session_manager.py` | Session secrets, ownership validation |
| `session_service.py` | Return type update (str → dict) |
| `app.py` | Session creation endpoint update |
| `query_classifier.py` | Small talk, conv actions, softened gating |
| `orchestrator.py` | Conv handling, context memory, empty failure reduction |
| `response_synthesizer.py` | Tone modes, token safety, executive structuring |
| `schemas.py` | ClassificationTrace extended fields |

---

## Validation (Phase 10)

### SQL Security — ✅ All Passing
- UNION injection → Blocked
- sqlite_master access → Blocked
- Unknown table → Blocked
- Recursive CTE → Blocked
- Multi-statement → Blocked

### Conversation — ✅ All Passing
- "hello" → Greeting response (no retrieval)
- "what can you do" → Capability response (no retrieval)
- "thanks" → Acknowledgement (no retrieval)

### Domain Gating — ✅ All Passing
- "create a summary" → Allowed
- "create python code" → Blocked

### Classifier Logic — ✅ All Passing
- "what do you mean by X" → clarification_request
- "use bullet points" → formatting_request
---

## Part 4: Analytical Presentation & Visualization

### Phase 10 — Structured Data Extraction ✅
**File:** `backend/api/services/response_synthesizer.py`
- Implemented `_extract_structured_data()` — transforms SQL results/Markdown tables into JSON
- Added `_extract_flattened_table()` — uses regex heuristics to reconstruct tables from RAG text
- Supports: `metric_comparison`, `trend_analysis`, `breakdown_analysis`, `table_response`
- Handles percentages (`%`), financial units (`$`, `M`, `K`), and ID-like exclusion

### Phase 11 — High-Fidelity UI Components ✅
**File:** `frontend/src/components/AnalyticalComponents.tsx`, `MessageBubble.tsx`
- Created `DataTable`: Responsive, styled table with hover states and column formatting
- Created `DataChart`: CSS-driven bar/line charts with animated gradients and scaling
- Created `KPICard`: Highlight metrics for singular data points
- Added `Executive Header`: Professional titles and metadata badges for analytical responses

### Phase 12 — Smart Labeling & Outlier Logic ✅
**File:** `backend/api/services/response_synthesizer.py`
- Added **Diversity-Weighted Category Selection**: Skips constant columns (e.g., "ERROR") in favor of descriptive ones (e.g., "Table Name")
- Added **ID Hardening**: Automatically excludes large whole-number IDs from being misinterpreted as metrics
- Added **Label Cleaning**: Strips redundant header text from extracted metrics for cleaner chart labels

---

## Status: PROJECT COMPLETE ✅
- Security & Robustness: Hardened
- Conversational UX: Fluid
- Analytical Insights: Visualized
- Executive Dashboard: Finalized
