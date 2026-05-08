"""
Module: orchestrator.py
Purpose: Securely coordinates Text-to-SQL and Semantic Document Retrieval systems.
Responsibilities: Validates queries, delegates execution to appropriate tools, and formats LLM context.
Security Boundaries: Strictly firewalls LLMs from the raw databases and documents. Exposes only heavily bounded snippets.
Key Decisions: Abstracted the final context generation natively so the orchestrator inherently enforces data access limits.
Inputs: User query, environment name, optional generated SQL.
Outputs: Traced, token-optimized LLM response payload.
"""
import uuid
import time
import json
from backend.orchestration.query_classifier import classify_query
from backend.orchestration.retrieval_tools import search_documents, query_structured_data, format_document_results, format_sql_results
from backend.logging_utils import get_file_logger
from backend.schemas import QueryRequest, QueryResponse, QueryTrace, ClassificationTrace
from backend.exceptions import UnsafeQueryError, RetrievalError

def _mock_text_to_sql_llm(user_query: str, dataset_name: str) -> str:
    """Mock LLM capability representing a Text-to-SQL generation step."""
    query_lower = user_query.lower()
    if "apac" in query_lower and "revenue" in query_lower:
        return "SELECT spend_usd as revenue, platform FROM marketing_campaigns WHERE region='APAC' LIMIT 5;"
    elif "top 10 movies" in query_lower:
        return "SELECT m.title, w.completion_rate FROM watch_activity w JOIN movies m ON w.movie_id = m.movie_id ORDER BY w.completion_rate DESC LIMIT 10;"
    elif "watch hours drop" in query_lower:
        return "SELECT quarter, total_watch_hours FROM regional_performance LIMIT 4;"
    return "SELECT * FROM regional_performance LIMIT 5;"

def orchestrate_query(request: QueryRequest, generated_sql: str = None) -> QueryResponse:
    """
    Coordinates SQL + Retrieval tools securely using fully typed Pydantic models.
    """
    start_time = time.time()
    req_id = request.request_id or str(uuid.uuid4())[:8]
    dataset = request.dataset
    user_query = request.query
    
    logger = get_file_logger(dataset)
    logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Inbound query received: '{user_query}'")
    
    # 1. Flow: Classify Query & Select Tools
    classification_dict = classify_query(user_query)
    classification = ClassificationTrace(**classification_dict)
    
    logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Route assigned: {classification.query_type.upper()} (Confidence: {classification.confidence})")
    
    answer_context = []
    tool_executions = []
    sources = []
    warnings = []
    errors = []
    
    # 2. Flow: Execute Tools (SQL)
    if "query_structured_data" in classification.recommended_tools:
        logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Executing structured SQL path...")
        sql_to_run = generated_sql if generated_sql else _mock_text_to_sql_llm(user_query, dataset)
        try:
            rows, sql_trace = query_structured_data(sql_to_run, dataset, req_id)
            tool_executions.append(sql_trace)
            answer_context.append(format_sql_results(rows, sql_to_run))
            sources.extend([f"DB_TABLE:{t.upper()}" for t in sql_trace.table_references])
        except UnsafeQueryError as e:
            errors.append(f"SQL Guard rejected query: {e}")
            warnings.append("Partial context: SQL results missing due to safety violation.")
            
    # 3. Flow: Execute Tools (PDF)
    if "search_documents" in classification.recommended_tools:
        logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Executing semantic PDF retrieval path...")
        try:
            doc_results, doc_trace = search_documents(user_query, dataset, req_id, n_results=3)
            tool_executions.append(doc_trace)
            answer_context.append(format_document_results(doc_results))
            for res in doc_results:
                sources.append(f"PDF:{res.source_file} (Page {res.page_number} | ID:{res.chunk_id[:8]}...)")
        except RetrievalError as e:
            errors.append(f"Document Retrieval failed: {e}")
            warnings.append("Partial context: Semantic search unavailable.")
            
    # 4. Prepare LLM-Safe Response Payload
    final_context = "\n\n".join(answer_context)
    if not final_context.strip():
        final_context = "No relevant context could be retrieved securely."
        
    total_time = round((time.time() - start_time) * 1000, 2)
    
    trace = QueryTrace(
        request_id=req_id,
        dataset=dataset,
        classification=classification,
        tool_executions=tool_executions,
        total_timing_ms=total_time
    )
    
    response = QueryResponse(
        request_id=req_id,
        answer_context=final_context,
        sources=list(set(sources)),
        trace=trace,
        overall_confidence=classification.confidence,
        warnings=warnings,
        errors=errors
    )
    
    logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Assembly complete in {total_time}ms. Sources: {len(response.sources)}")
    return response

if __name__ == "__main__":
    dataset = "vistastream"
    
    print("="*60)
    print("TEST: HYBRID MULTI-SOURCE ORCHESTRATION")
    print("="*60)
    
    req = QueryRequest(query="Why did our watch hours drop in Q3, and does the executive report explain it?", dataset=dataset)
    res = orchestrate_query(req)
    print(res.model_dump_json(indent=2))
