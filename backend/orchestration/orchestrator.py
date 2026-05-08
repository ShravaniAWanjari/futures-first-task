"""
Module: orchestrator.py
Purpose: Securely coordinates Text-to-SQL and Semantic Document Retrieval systems.
"""
import uuid
import time
import json
from typing import List, Optional, Dict, Any
from backend.orchestration.query_classifier import classify_query
from backend.orchestration.retrieval_tools import search_documents, query_structured_data, format_document_results, format_sql_results
from backend.logging_utils import get_file_logger
from backend.schemas import QueryRequest, QueryResponse, QueryTrace, ClassificationTrace
from backend.exceptions import UnsafeQueryError, RetrievalError
from backend.config import Config


def _mock_text_to_sql_llm(user_query: str, dataset_name: str) -> Optional[str]:
    """
    Mock LLM capability representing a Text-to-SQL generation step.
    Implements schema-aware grounding for management dimensions.
    """
    query_lower = user_query.lower()

    # 1. Dimension Detection: Region vs Platform
    is_regional = any(word in query_lower for word in ["region", "europe", "apac", "na", "north america", "latam", "emerging market"])
    is_platform = any(word in query_lower for word in ["platform", "channel", "youtube", "tiktok", "instagram", "tv"])
    
    # 2. Metric Detection
    is_spend = any(word in query_lower for word in ["spend", "cost", "ad-spend", "efficiency", "roi"])
    is_growth = any(word in query_lower for word in ["growth", "subscriber", "new_subscriber"])
    is_performance = any(word in query_lower for word in ["performance", "watch hours", "completion"])

    # 3. Operational Domain Detection (Direct Routing)
    is_ingestion = any(word in query_lower for word in ["ingestion", "upload", "inbound"])
    is_validation = any(word in query_lower for word in ["validation", "rejected", "failed", "error"])
    is_data_quality = any(word in query_lower for word in ["data quality", "inconsistency", "duplicate"])

    # --- Scenario: Ingestion Quality / Logs ---
    if is_ingestion or is_data_quality:
        return "SELECT category, status_code, COUNT(*) as occurrence FROM ingestion_logs GROUP BY category, status_code ORDER BY occurrence DESC;"
    
    # --- Scenario: Validation / Rejections ---
    if is_validation:
        return "SELECT validation_rule, rejected_count, impact_severity FROM validation_summaries WHERE rejected_count > 0 ORDER BY impact_severity DESC;"

    # --- Scenario: Regional Comparison (Highest Priority for management) ---
    if is_regional and is_spend:
        # User asked for regional spend/efficiency
        return "SELECT region, SUM(spend_usd) as total_spend, AVG(spend_usd/impressions)*1000 as cpm_efficiency FROM marketing_campaigns GROUP BY region ORDER BY total_spend DESC LIMIT 5;"
    
    if is_regional and is_performance:
        return "SELECT region, SUM(total_watch_hours) as watch_performance, AVG(churn_rate) as churn_risk FROM regional_performance GROUP BY region ORDER BY watch_performance DESC;"

    # --- Scenario: Specific Comparison Follow-up ---
    if "compare" in query_lower and "europe" in query_lower and "apac" in query_lower:
        if is_spend:
            return "SELECT region, SUM(spend_usd) as ad_spend, SUM(impressions) as reach FROM marketing_campaigns WHERE region IN ('Europe', 'APAC') GROUP BY region;"
        return "SELECT region, total_watch_hours, new_subscribers FROM regional_performance WHERE region IN ('Europe', 'APAC');"

    # --- Scenario: Platform/Channel (Specific) ---
    if is_platform:
        if is_spend:
            return "SELECT platform, SUM(spend_usd) as platform_spend FROM marketing_campaigns GROUP BY platform ORDER BY platform_spend DESC LIMIT 5;"
        return "SELECT platform, impressions, spend_usd FROM marketing_campaigns LIMIT 5;"

    # --- Scenario: Correlation / Relationship ---
    if "correlate" in query_lower or "relationship" in query_lower:
        if "spend" in query_lower and "performance" in query_lower:
            # Join simulation
            return "SELECT r.region, m.spend_usd, r.total_watch_hours FROM regional_performance r JOIN marketing_campaigns m ON r.region = m.region LIMIT 5;"

    # --- Scenario: General Metrics ---
    if is_growth:
        return "SELECT region, new_subscribers, completion_rate FROM regional_performance ORDER BY new_subscribers DESC LIMIT 5;"
    
    if is_spend:
        return "SELECT region, SUM(spend_usd) as spend FROM marketing_campaigns GROUP BY region LIMIT 5;"

    return None


def orchestrate_query(request: QueryRequest, history: List[Dict[str, Any]] = None, generated_sql: str = None) -> QueryResponse:
    """
    Coordinates SQL + Retrieval tools with conversational grounding.
    """
    start_time = time.time()
    req_id = request.request_id or str(uuid.uuid4())[:8]
    dataset = request.dataset
    user_query = request.query
    
    logger = get_file_logger(dataset)
    logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Inbound query: '{user_query}'")
    
    # 1. Classify with History
    classification_dict = classify_query(user_query, history)
    
    # Intent Inheritance for follow-ups
    if classification_dict.get('query_type') == 'hybrid' and classification_dict.get('confidence') < 0.7:
        # Check if we can inherit from history
        if history:
            for msg in reversed(history):
                if msg.get('role') == 'assistant' and msg.get('trace'):
                    try:
                        prev_trace = json.loads(msg['trace'])
                        prev_type = prev_trace['classification']['query_type']
                        if prev_type in ['sql', 'pdf']:
                            classification_dict['query_type'] = prev_type
                            classification_dict['recommended_tools'] = prev_trace['classification']['recommended_tools']
                            classification_dict['confidence'] = 0.8  # Inherited confidence
                            classification_dict['reasoning'] += f" Inheriting intent from prior {prev_type} interaction."
                            break
                    except: continue

    classification = ClassificationTrace(**classification_dict)
    
    # Use resolved query for actual tool execution if it exists
    execution_query = classification_dict.get('resolved_query', user_query)
    
    logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Resolved Query: '{execution_query}'")
    logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Route: {classification.query_type.upper()} (Confidence: {classification.confidence})")
    
    answer_context = []
    tool_executions = []
    sources = []
    warnings = []
    errors = []
    
    retrieval_limit = 2 if Config.DEMO_MODE else 5
    
    # 2. Execute Tools in Priority Order
    for tool_name in classification.recommended_tools:
        if tool_name == "query_structured_data":
            logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Executing SQL path...")
            sql_to_run = generated_sql if generated_sql else _mock_text_to_sql_llm(execution_query, dataset)
            
            if not sql_to_run:
                logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] No SQL generated for resolved query.")
                continue
                
            try:
                rows, sql_trace = query_structured_data(sql_to_run, dataset, req_id)
                tool_executions.append(sql_trace)
                
                # Check for context priority
                if classification.recommended_tools[0] == "query_structured_data":
                    answer_context.insert(0, format_sql_results(rows, sql_to_run))
                else:
                    answer_context.append(format_sql_results(rows, sql_to_run))
                
                sources.extend([f"DB_TABLE:{t.upper()}" for t in sql_trace.table_references])
            except UnsafeQueryError as e:
                errors.append(f"SQL Guard rejected query: {e}")
            
        elif tool_name == "search_documents":
            logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Executing PDF path...")
            try:
                doc_results, doc_trace = search_documents(execution_query, dataset, req_id, n_results=retrieval_limit)
                tool_executions.append(doc_trace)
                
                if classification.recommended_tools[0] == "search_documents":
                    answer_context.insert(0, format_document_results(doc_results))
                else:
                    answer_context.append(format_document_results(doc_results))
                
                for res in doc_results:
                    sources.append(f"PDF:{res.source_file} (Page {res.page_number} | ID:{res.chunk_id[:8]}...)")
            except RetrievalError as e:
                errors.append(f"Document Retrieval failed: {e}")

    # 3. Final Context
    final_context = "\n\n".join(answer_context)
    if not final_context.strip():
        if classification.confidence < 0.7:
            final_context = "The system could not confidently identify relevant operational data using the currently available sources. Re-phrasing the request with specific metrics or regions may help."
        else:
            final_context = "No specific operational records matching this query were found in the current workspace."
        
    total_time = round((time.time() - start_time) * 1000, 2)
    
    trace = QueryTrace(
        request_id=req_id,
        dataset=dataset,
        classification=classification,
        tool_executions=tool_executions,
        total_timing_ms=total_time
    )
    
    return QueryResponse(
        request_id=req_id,
        answer_context=final_context,
        sources=list(set(sources)),
        trace=trace,
        overall_confidence=classification.confidence,
        warnings=warnings,
        errors=errors
    )
