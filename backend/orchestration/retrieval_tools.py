"""
Module: retrieval_tools.py
Purpose: The functional unified tool interface exposed to LLM orchestration agents.
Responsibilities: Provides discrete semantic document search and structured SQL execution endpoints.
Security Boundaries: Automatically filters results down to strict limits (e.g. 15 rows) to prevent LLM context window blowouts.
Key Decisions: Enforces explicit `table_references` outputs for absolute hallucination prevention and traceability mapping.
Inputs: Queries, dataset environment strings.
Outputs: Standardized dictionary outputs formatted via clean Markdown converters.
"""
import os
import time
from typing import Dict, Any, List, Tuple

try:
    import chromadb
except ImportError:
    chromadb = None

from backend.orchestration.sql_guard import execute_safe_sql
from backend.logging_utils import get_file_logger
from backend.exceptions import RetrievalError, UnsafeQueryError
from backend.schemas import RetrievalResult, RetrievalTrace, SQLTrace
from backend.config import Config

def get_chroma_client():
    if chromadb is None:
        raise RetrievalError("ChromaDB is not installed.")
    return chromadb.PersistentClient(path=Config.CHROMA_DB_PATH)

def get_db_path(dataset_name: str) -> str:
    if dataset_name == "vistastream":
        return Config.VISTASTREAM_DB_PATH
    return Config.NEONPLAY_DB_PATH

# --- FORMATTING HELPERS ---

def format_document_results(results: List[RetrievalResult]) -> str:
    if not results:
        return "No documents found matching the semantic query."
        
    formatted = "=== SEMANTIC SEARCH RESULTS ===\n"
    for i, res in enumerate(results, 1):
        formatted += f"\n[Document Result {i}] (Confidence: {res.confidence:.2f})\n"
        formatted += f"Source File: {res.source_file} (Page {res.page_number})\n"
        formatted += f"Section: {res.section_title}\n"
        formatted += f"Snippet: {res.snippet_text}\n"
        formatted += f"Trace ID: {res.chunk_id}\n"
    return formatted

def format_sql_results(rows: List[Dict[str, Any]], query: str) -> str:
    if not rows:
        return f"=== SQL EXECUTION RESULTS ===\nExecuted Query: {query}\nReturned 0 rows.\n"
        
    formatted = "=== SQL EXECUTION RESULTS ===\n"
    formatted += f"Executed Query: {query}\n"
    formatted += f"Returned {len(rows)} rows.\n\n"
    
    keys = list(rows[0].keys())
    formatted += " | ".join(str(k) for k in keys) + "\n"
    formatted += "-" * min(80, (len(keys) * 15)) + "\n"
    
    for row in rows[:15]: 
        formatted += " | ".join(str(row.get(k, "")) for k in keys) + "\n"
        
    if len(rows) > 15:
        formatted += f"... and {len(rows) - 15} more rows omitted.\n"
        
    return formatted

# --- RETRIEVAL ABSTRACTIONS ---

def search_documents(query: str, dataset_name: str, request_id: str = "UNKNOWN", n_results: int = 3) -> Tuple[List[RetrievalResult], RetrievalTrace]:
    logger = get_file_logger(dataset_name)
    start_time = time.time()
    trace = RetrievalTrace(success=False, n_results=0)
    
    try:
        client = get_chroma_client()
        collection_name = f"{dataset_name}_documents"
        
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            raise RetrievalError(f"Collection '{collection_name}' not found. Verify embeddings were generated.")
            
        chroma_res = collection.query(query_texts=[query], n_results=n_results)
        
        parsed_results = []
        if chroma_res['ids'] and chroma_res['ids'][0]:
            for idx, chunk_id in enumerate(chroma_res['ids'][0]):
                meta = chroma_res['metadatas'][0][idx]
                dist = chroma_res['distances'][0][idx] if 'distances' in chroma_res and chroma_res['distances'] else 1.0
                doc_text = chroma_res['documents'][0][idx]
                
                # Simple confidence heuristic based on distance
                conf = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                
                res = RetrievalResult(
                    chunk_id=chunk_id,
                    source_file=meta.get("source_file", "Unknown"),
                    page_number=meta.get("page_number", -1),
                    section_title=meta.get("section_title", "Unknown"),
                    snippet_text=doc_text,
                    similarity_score=float(dist),
                    confidence=conf
                )
                parsed_results.append(res)
                
        trace.success = True
        trace.n_results = len(parsed_results)
        trace.timing_ms = round((time.time() - start_time) * 1000, 2)
        
        logger.info(f"[{dataset_name}] [REQ:{request_id}] [retrieval_doc] Semantic search completed in {trace.timing_ms}ms.")
        return parsed_results, trace
        
    except Exception as e:
        trace.error = str(e)
        trace.timing_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"[{dataset_name}] [REQ:{request_id}] [retrieval_doc] Exception during search: {e}")
        raise RetrievalError(str(e))

def query_structured_data(sql_query: str, dataset_name: str, request_id: str = "UNKNOWN") -> Tuple[List[Dict[str, Any]], SQLTrace]:
    db_path = get_db_path(dataset_name)
    logger = get_file_logger(dataset_name)
    logger.info(f"[{dataset_name}] [REQ:{request_id}] [retrieval_sql] Incoming query execution request.")
    
    # execute_safe_sql raises UnsafeQueryError natively
    rows, sql_trace = execute_safe_sql(db_path, dataset_name, sql_query, request_id)
    return rows, sql_trace
