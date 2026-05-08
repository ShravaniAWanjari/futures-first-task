"""
Module: orchestrator.py
Purpose: Securely coordinates Text-to-SQL and Semantic Document Retrieval systems.
Responsibilities: Validates queries, delegates execution to appropriate tools, and formats LLM context.
Security Boundaries: Strictly firewalls LLMs from the raw databases and documents. Exposes only heavily bounded snippets.
Key Decisions: Abstracted the final context generation natively so the orchestrator inherently enforces data access limits.
Inputs: User query, environment name, optional generated SQL.
Outputs: Traced, token-optimized LLM response payload.
"""

import json
from query_classifier import classify_query
from retrieval_tools import search_documents, query_structured_data, format_document_results, format_sql_results
from logging_utils import get_file_logger

def _mock_text_to_sql_llm(user_query: str, dataset_name: str) -> str:
    """
    Mock LLM capability representing a Text-to-SQL generation step.
    In a live production system, an LLM would use the DB schema to dynamically generate this SQL.
    """
    query_lower = user_query.lower()
    if "apac" in query_lower and "revenue" in query_lower:
        # Intentionally hitting marketing campaigns for spend/revenue simulation
        return "SELECT spend_usd as revenue, platform FROM marketing_campaigns WHERE region='APAC' LIMIT 5;"
    elif "top 10 movies" in query_lower:
        return "SELECT m.title, w.completion_rate FROM watch_activity w JOIN movies m ON w.movie_id = m.movie_id ORDER BY w.completion_rate DESC LIMIT 10;"
    elif "watch hours drop" in query_lower:
        return "SELECT quarter, total_watch_hours FROM regional_performance LIMIT 4;"
    
    return "SELECT * FROM regional_performance LIMIT 5;"

def orchestrate_query(user_query: str, dataset_name: str, generated_sql: str = None) -> dict:
    """
    Coordinates SQL + Retrieval tools securely.
    Acts as the strict firewall between raw data stores and the final LLM reasoning layer.
    """
    logger = get_file_logger(dataset_name)
    logger.info(f"[{dataset_name}] [orchestrator] Inbound query received: '{user_query}'")
    
    # 1. Flow: Classify Query & Select Tools
    classification = classify_query(user_query)
    query_type = classification["query_type"]
    tools_to_run = classification["recommended_tools"]
    
    logger.info(f"[{dataset_name}] [orchestrator] Route assigned: {query_type.upper()} (Confidence: {classification['confidence']})")
    
    answer_context = []
    trace_metadata = {
        "classification": classification,
        "tool_executions": []
    }
    sources = []
    
    # 2. Flow: Execute Tools (SQL)
    if "query_structured_data" in tools_to_run:
        logger.info(f"[{dataset_name}] [orchestrator] Executing structured SQL path...")
        
        # If no explicit SQL was handed off by an external agent, use our mock text-to-sql translation
        sql_to_run = generated_sql if generated_sql else _mock_text_to_sql_llm(user_query, dataset_name)
        
        sql_res = query_structured_data(sql_to_run, dataset_name)
        
        trace_metadata["tool_executions"].append({
            "tool": "query_structured_data",
            "success": sql_res["success"],
            "query_used": sql_to_run,
            "error": sql_res.get("error")
        })
        
        # 3. Assemble Context (LLM only receives safe validated output, never raw DB)
        answer_context.append(format_sql_results(sql_res))
        
        if sql_res["success"]:
            for table in sql_res.get("table_references", []):
                sources.append(f"DB_TABLE:{table.upper()}")
                
    # 4. Flow: Execute Tools (PDF)
    if "search_documents" in tools_to_run:
        logger.info(f"[{dataset_name}] [orchestrator] Executing semantic PDF retrieval path...")
        
        doc_res = search_documents(user_query, dataset_name, n_results=3)
        
        trace_metadata["tool_executions"].append({
            "tool": "search_documents",
            "success": doc_res["success"],
            "n_results": len(doc_res.get("results", [])),
            "error": doc_res.get("error")
        })
        
        # Assemble Context (LLM only receives bounded snippets, not unrestricted documents)
        answer_context.append(format_document_results(doc_res.get("results", [])))
        
        if doc_res["success"]:
            for res in doc_res.get("results", []):
                sources.append(f"PDF:{res['source_file']} (Page {res['page_number']} | ID:{res['chunk_id'][:8]}...)")
                
    # 5. Prepare LLM-Safe Response Payload
    final_context = "\n\n".join(answer_context)
    
    response = {
        "answer_context": final_context,
        "trace": trace_metadata,
        "sources": list(set(sources)) # Deduplicate references
    }
    
    logger.info(f"[{dataset_name}] [orchestrator] Assembly complete. Identified {len(response['sources'])} distinct data sources.")
    
    return response

if __name__ == "__main__":
    dataset = "vistastream"
    
    print("="*60)
    print("TEST 1: SQL-ONLY ORCHESTRATION")
    print("="*60)
    res1 = orchestrate_query("What was the total revenue in APAC last quarter?", dataset)
    print(json.dumps(res1, indent=2))
    print("\n")
    
    print("="*60)
    print("TEST 2: PDF-ONLY ORCHESTRATION")
    print("="*60)
    res2 = orchestrate_query("What are the official guidelines for handling malformed CSV uploads?", dataset)
    print(json.dumps(res2, indent=2))
    print("\n")
    
    print("="*60)
    print("TEST 3: HYBRID MULTI-SOURCE ORCHESTRATION")
    print("="*60)
    res3 = orchestrate_query("Why did our watch hours drop in Q3, and does the executive report explain it?", dataset)
    print(json.dumps(res3, indent=2))
    print("\n")
