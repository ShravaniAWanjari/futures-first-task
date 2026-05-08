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
import re
from typing import Dict, Any, List

try:
    import chromadb
except ImportError:
    chromadb = None

from sql_guard import execute_safe_sql
from logging_utils import get_file_logger

def get_chroma_client():
    """Returns a persistent ChromaDB client mapped to our standard directory."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    chroma_dir = os.path.join(base_dir, "chroma")
    if chromadb is None:
        return None
    return chromadb.PersistentClient(path=chroma_dir)

def get_db_path(dataset_name: str) -> str:
    """Resolves the physical SQLite DB path for the environment."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "databases", f"{dataset_name}.db")

# --- FORMATTING HELPERS ---

def format_document_results(results: List[Dict[str, Any]]) -> str:
    """Formats semantic document search results into a clean text block for LLM prompts."""
    if not results:
        return "No documents found matching the semantic query."
        
    formatted = "=== SEMANTIC SEARCH RESULTS ===\n"
    for i, res in enumerate(results, 1):
        formatted += f"\n[Document Result {i}] (Distance: {res['similarity_score']:.4f})\n"
        formatted += f"Source File: {res['source_file']} (Page {res['page_number']})\n"
        formatted += f"Section: {res.get('section_title', 'Unknown')}\n"
        formatted += f"Snippet: {res['snippet_text']}\n"
        formatted += f"Trace ID: {res['chunk_id']}\n"
    return formatted

def format_sql_results(sql_result: Dict[str, Any]) -> str:
    """Formats SQL execution output into an easy-to-read textual table representation."""
    if not sql_result["success"]:
        return f"=== SQL EXECUTION ERROR ===\nError: {sql_result['error']}\nQuery: {sql_result['query']}"
        
    formatted = "=== SQL EXECUTION RESULTS ===\n"
    formatted += f"Executed Query: {sql_result['query']}\n"
    rows = sql_result["rows"]
    
    if not rows:
        formatted += "Returned 0 rows.\n"
        return formatted
        
    formatted += f"Returned {len(rows)} rows.\n\n"
    
    keys = list(rows[0].keys())
    formatted += " | ".join(str(k) for k in keys) + "\n"
    formatted += "-" * min(80, (len(keys) * 15)) + "\n"
    
    for row in rows[:15]: # Soft limit to prevent blowing up context windows
        formatted += " | ".join(str(row.get(k, "")) for k in keys) + "\n"
        
    if len(rows) > 15:
        formatted += f"... and {len(rows) - 15} more rows omitted.\n"
        
    return formatted

# --- RETRIEVAL ABSTRACTIONS ---

def search_documents(query: str, dataset_name: str, n_results: int = 3) -> Dict[str, Any]:
    """
    Semantic retrieval interface for PDF documents via ChromaDB.
    Maintains strict environment isolation via dataset_name.
    """
    logger = get_file_logger(dataset_name)
    response = {
        "success": False,
        "query": query,
        "results": [],
        "trace": {"dataset": dataset_name, "n_requested": n_results},
        "error": None
    }
    
    if chromadb is None:
        response["error"] = "ChromaDB is not available on the system."
        return response
        
    client = get_chroma_client()
    collection_name = f"{dataset_name}_documents"
    
    try:
        collection = client.get_collection(name=collection_name)
    except Exception as e:
        response["error"] = f"Collection '{collection_name}' not found. Verify embeddings were generated."
        return response
        
    try:
        chroma_res = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        parsed_results = []
        if chroma_res['ids'] and chroma_res['ids'][0]:
            for idx, chunk_id in enumerate(chroma_res['ids'][0]):
                meta = chroma_res['metadatas'][0][idx]
                dist = chroma_res['distances'][0][idx] if 'distances' in chroma_res and chroma_res['distances'] else 0.0
                doc_text = chroma_res['documents'][0][idx]
                
                parsed_results.append({
                    "chunk_id": chunk_id,
                    "source_file": meta.get("source_file", "Unknown"),
                    "page_number": meta.get("page_number", -1),
                    "section_title": meta.get("section_title", "Unknown"),
                    "snippet_text": doc_text,
                    "similarity_score": float(dist)
                })
                
        response["success"] = True
        response["results"] = parsed_results
        response["trace"]["n_returned"] = len(parsed_results)
        logger.info(f"[{dataset_name}] [retrieval_doc] Semantic search for '{query}' returned {len(parsed_results)} results.")
        
    except Exception as e:
        response["error"] = str(e)
        logger.error(f"[{dataset_name}] [retrieval_doc] Exception during search: {e}")
        
    return response

def query_structured_data(sql_query: str, dataset_name: str) -> Dict[str, Any]:
    """
    SQL retrieval interface leveraging the secure sql_guard.
    Maintains strict environment isolation via dataset_name.
    """
    db_path = get_db_path(dataset_name)
    logger = get_file_logger(dataset_name)
    
    logger.info(f"[{dataset_name}] [retrieval_sql] Incoming query execution request.")
    
    # Leverages the secure firewall layer implicitly
    sql_result = execute_safe_sql(db_path, dataset_name, sql_query)
    
    # Heuristically extract table references to enrich the traceability payload
    tables_found = list(set(re.findall(r"(?:FROM|JOIN)\s+([A-Za-z0-9_]+)", sql_query.upper())))
    
    response = {
        "success": sql_result["success"],
        "query": sql_query,
        "rows": sql_result.get("rows", []),
        "table_references": [t.lower() for t in tables_found],
        "trace": {
            "dataset": dataset_name,
            "sql_guard_trace": sql_result.get("trace", {})
        },
        "error": sql_result.get("error")
    }
    
    return response

if __name__ == "__main__":
    # Test script execution
    dataset = "vistastream"
    
    print("\n--- Testing Document Retrieval Abstraction ---")
    doc_res = search_documents("marketing spend and expansion strategy", dataset, n_results=2)
    print(format_document_results(doc_res["results"]))
    
    print("\n--- Testing SQL Retrieval Abstraction ---")
    sql_res = query_structured_data("SELECT region, total_watch_hours as hours FROM regional_performance LIMIT 3;", dataset)
    print(format_sql_results(sql_res))
