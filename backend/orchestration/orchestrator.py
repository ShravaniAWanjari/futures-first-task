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


def plan_and_generate_sql(intent: Optional[Dict[str, Any]], routing_plan: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Deterministically generates SQL based strictly on extracted intent and validated schema routing.
    Eliminates raw natural language prompting to prevent hallucinated queries.
    """
    if not intent or not routing_plan:
        return "SELECT * FROM regional_performance LIMIT 5;"

    metric = intent.get("metric", "")
    dimension = intent.get("dimension", "")
    domain = intent.get("domain", "")
    entities = intent.get("entities", [])
    target_tables = routing_plan.get("target_tables", [])
    extreme = intent.get("extreme") # highest, lowest
    
    logger.info(f"[orchestrator] Planning SQL for domain={domain}, entities={entities}, metric={metric}")
    
    if not target_tables:
        return None

    primary_table = target_tables[0]

    # 1. Strict Schema Definition (Actual DB Schema)
    SCHEMA = {
        "marketing_campaigns": ["region", "platform", "spend_usd", "impressions", "roi", "cpm", "reach", "spend"],
        "regional_performance": ["region", "total_watch_hours", "churn_rate", "new_subscribers", "completion_rate", "performance", "growth"],
        "ingestion_logs": ["log_id", "dataset", "source_file", "table_name", "row_reference", "log_level", "action_taken", "message", "timestamp"]
    }

    # 2. Validate Dimension against Schema
    valid_columns = SCHEMA.get(primary_table, [])
    if dimension and dimension not in valid_columns:
        # Fallback or error if hallucinated dimension
        return f"-- ERROR: Dimension '{dimension}' not found in target table '{primary_table}'"

    # 3. Construct Filters
    filters = []
    if entities:
        regions = [e for e in entities if e in ["APAC", "LATAM", "EMEA", "North America", "Europe"]]
        platforms = [e for e in entities if e in ["YouTube Shorts", "TikTok", "Instagram Reels", "Connected TV", "Google Ads"]]
        
        if regions and "region" in valid_columns:
            # Normalize classifier region aliases to database region values.
            region_aliases = {
                "EMEA": ["Europe"],
                "APAC": ["APAC"],
                "LATAM": ["LATAM"],
                "North America": ["North America"],
                "Europe": ["Europe"],
            }
            normalized_regions = []
            for region in regions:
                normalized_regions.extend(region_aliases.get(region, [region]))
            normalized_regions = list(dict.fromkeys(normalized_regions))
            entity_list = "', '".join(normalized_regions)
            filters.append(f"region IN ('{entity_list}')")
        if platforms and "platform" in valid_columns:
            entity_list = "', '".join(platforms)
            filters.append(f"platform IN ('{entity_list}')")

    where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""

    # 4. Phase 4: Deterministic Operational Query Templates
    if primary_table == "ingestion_logs" or domain in ["anomaly_detection", "duplicates", "ingestion_quality", "normalization_activity", "validation_errors"]:
        # Warning Analysis
        if domain == "anomaly_detection":
            return "SELECT log_level, action_taken, table_name, COUNT(*) as occurrence FROM ingestion_logs WHERE log_level IN ('WARNING', 'ERROR') GROUP BY log_level, action_taken, table_name ORDER BY occurrence DESC LIMIT 15;"
        
        # Duplicate Analysis
        if domain == "duplicates":
            return "SELECT log_level, action_taken, table_name, COUNT(*) as occurrence FROM ingestion_logs WHERE message LIKE '%duplicate%' GROUP BY log_level, action_taken, table_name ORDER BY occurrence DESC LIMIT 10;"
            
        # Normalization Issues
        if domain == "normalization_activity":
            return "SELECT log_level, action_taken, table_name, COUNT(*) as occurrence FROM ingestion_logs WHERE action_taken = 'normalized' GROUP BY log_level, action_taken, table_name ORDER BY occurrence DESC LIMIT 10;"

        # Ingestion Inconsistencies / Quality
        if domain == "ingestion_quality":
            return "SELECT log_level, action_taken, table_name, COUNT(*) as occurrence FROM ingestion_logs WHERE action_taken IN ('rejected', 'failed', 'error') GROUP BY log_level, action_taken, table_name ORDER BY occurrence DESC LIMIT 10;"

        # Validation Failures (Mapped to ingestion_logs as validation_summaries is missing)
        if domain == "validation_errors":
            return "SELECT log_level, action_taken, table_name, COUNT(*) as occurrence FROM ingestion_logs WHERE action_taken = 'rejected' OR log_level = 'ERROR' GROUP BY log_level, action_taken, table_name ORDER BY occurrence DESC LIMIT 10;"

    # 5. Generic Structured Query Fallback (Performance/Growth)
    if primary_table == "marketing_campaigns":
        group_col = dimension if dimension else "region"
        order_clause = ""
        if extreme == "highest": order_clause = " ORDER BY spend DESC"
        elif extreme == "lowest": order_clause = " ORDER BY spend ASC"
        
        if metric in ["roi", "efficiency"]:
            if extreme == "highest": order_clause = " ORDER BY cpm_efficiency DESC"
            elif extreme == "lowest": order_clause = " ORDER BY cpm_efficiency ASC"
            return f"SELECT {group_col}, SUM(spend_usd) as total_spend, AVG(spend_usd/impressions)*1000 as cpm_efficiency FROM {primary_table}{where_clause} GROUP BY {group_col}{order_clause} LIMIT 5;"
            
        return f"SELECT {group_col}, SUM(spend_usd) as spend FROM {primary_table}{where_clause} GROUP BY {group_col}{order_clause} LIMIT 5;"

    if primary_table == "regional_performance":
        group_col = dimension if dimension else "region"
        if metric == "growth":
            return f"SELECT {group_col}, new_subscribers, completion_rate FROM {primary_table}{where_clause} ORDER BY new_subscribers DESC LIMIT 5;"
        return f"SELECT {group_col}, SUM(total_watch_hours) as watch_performance, AVG(churn_rate) as churn_risk FROM {primary_table}{where_clause} GROUP BY {group_col} ORDER BY watch_performance DESC LIMIT 10;"

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
    
    # Phase 7: Handle conversational (small talk) queries immediately
    if classification_dict.get('query_type') == 'conversational':
        conv_response = classification_dict.get('conversational_response', 'How can I help you?')
        total_time = round((time.time() - start_time) * 1000, 2)
        trace = QueryTrace(
            request_id=req_id, dataset=dataset,
            classification=ClassificationTrace(**classification_dict),
            tool_executions=[], total_timing_ms=total_time
        )
        logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Small talk handled. No retrieval.")
        return QueryResponse(
            request_id=req_id, answer_context=conv_response,
            sources=[], trace=trace, overall_confidence=1.0,
            warnings=[], errors=[]
        )
    
    # Part2-Phase2: Build Context Memory Window from recent history
    context_memory = ""
    if history:
        for msg in reversed(history[-6:]):
            if msg.get('role') == 'assistant' and msg.get('content'):
                context_memory = msg['content']
                break
    
    # Intent Inheritance for follow-ups (Phase 2 & 4)
    memory_inheritance = False
    inheritance_reason = "No follow-up detected."
    follow_up_detected = classification_dict.get('follow_up_detected', False)
    
    if follow_up_detected and history:
        # Check if we can inherit from history
        for msg in reversed(history):
            if msg.get('role') == 'assistant' and msg.get('trace'):
                try:
                    raw_trace = msg.get('trace')
                    prev_trace = json.loads(raw_trace) if isinstance(raw_trace, str) else raw_trace
                    if not isinstance(prev_trace, dict):
                        continue
                    prev_type = prev_trace['classification']['query_type']
                    if prev_type in ['sql', 'pdf']:
                        classification_dict['query_type'] = prev_type
                        classification_dict['recommended_tools'] = prev_trace['classification']['recommended_tools']
                        classification_dict['confidence'] = 0.9  # Intentional inheritance
                        classification_dict['reasoning'] += f" Inheriting intent from prior {prev_type} follow-up."
                        
                        if 'intent' in prev_trace['classification']:
                            classification_dict['intent'] = prev_trace['classification']['intent']
                        if 'routing_plan' in prev_trace['classification']:
                            classification_dict['routing_plan'] = prev_trace['classification']['routing_plan']
                        
                        memory_inheritance = True
                        inheritance_reason = f"Explicit follow-up detected. Inheriting {prev_type} context."
                        break
                except Exception:
                    continue
    
    memory_trace = {
        "memory_inheritance": memory_inheritance,
        "inheritance_reason": inheritance_reason,
        "follow_up_detected": follow_up_detected
    }
    logger.info(f"[{dataset}] [REQ:{req_id}] [MEMORY_DEBUG] {json.dumps(memory_trace)}")

    classification = ClassificationTrace(**classification_dict)
    
    # Use resolved query for actual tool execution if it exists
    execution_query = classification_dict.get('resolved_query', user_query)
    
    # Semantic Search Optimization: Strip common framing words for better embedding matches (Phase 11)
    if classification.query_type == 'pdf' and len(execution_query.split()) < 10:
        framing_words = ["summarize", "list", "provide", "show", "me", "the", "for"]
        words = execution_query.split()
        refined_words = [w for w in words if w.lower() not in framing_words]
        if refined_words:
            execution_query = " ".join(refined_words)
            logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Refined execution query for embedding: '{execution_query}'")
    
    logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Resolved Query: '{execution_query}'")
    logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Route: {classification.query_type.upper()} (Confidence: {classification.confidence})")
    
    if classification.routing_plan:
        targets = classification.routing_plan.target_tables if classification.routing_plan.primary_route == 'sql' else classification.routing_plan.target_collections
        logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Routing Plan: strategy={classification.routing_plan.retrieval_strategy}, targets={targets}")
    
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
            sql_to_run = generated_sql if generated_sql else plan_and_generate_sql(
                classification_dict.get('intent'), 
                classification_dict.get('routing_plan')
            )
            
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
                doc_results, doc_trace = search_documents(
                    query=execution_query, 
                    dataset_name=dataset, 
                    request_id=req_id, 
                    n_results=retrieval_limit,
                    intent=classification_dict.get('intent')
                )
                tool_executions.append(doc_trace)
                
                if classification.recommended_tools[0] == "search_documents":
                    answer_context.insert(0, format_document_results(doc_results))
                else:
                    answer_context.append(format_document_results(doc_results))
                
                for res in doc_results:
                    sources.append(f"PDF:{res.source_file} (Page {res.page_number})")
            except RetrievalError as e:
                errors.append(f"Document Retrieval failed: {e}")

    # 3. Final Context
    final_context = "\n\n".join(answer_context)
    conv_action = classification_dict.get('conversational_action')
    
    if classification.query_type == "blocked":
        final_context = classification.reasoning
    elif not final_context.strip():
        # Part2-Phase6: Try context memory before failing
        if context_memory and (conv_action or follow_up_detected):
            final_context = context_memory
            logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Falling back to context memory (action={conv_action}).")
        elif classification.confidence < 0.7 and not any(tool.success for tool in tool_executions if tool.tool == 'search_documents'):
            final_context = "I couldn't find definitive operational evidence matching all parts of your query (topics: " + ", ".join(detected_domains or ["general"]) + "). \n\nTry rephrasing with specific metrics (ROI, Spend, Growth) or time periods (Q1, Q2 FY2026). For example: 'What were the Q2 regional highlights?'"
        elif not final_context.strip() or "No strongly relevant" in final_context:
            final_context = "No specific records matching your query were found in the current " + dataset.title() + " workspace. I've scanned both document reports and structured databases, but the specific combination of entities you requested is not available."
    elif (
        follow_up_detected
        and conv_action in ["refinement_request", "continuation_request", "clarification_request", "formatting_request"]
        and context_memory
        and "No strongly relevant document evidence was found." in final_context
    ):
        # For conversational follow-ups like "explain in more detail", prefer
        # elaborating from the last grounded assistant answer over empty retrieval.
        final_context = context_memory
        logger.info(f"[{dataset}] [REQ:{req_id}] [orchestrator] Using context memory due to empty follow-up retrieval.")
        
    total_time = round((time.time() - start_time) * 1000, 2)
    
    trace = QueryTrace(
        request_id=req_id,
        dataset=dataset,
        classification=classification,
        tool_executions=tool_executions,
        total_timing_ms=total_time
    )
    
    # --- PHASE 6: ROUTING DEBUG OUTPUT ---
    routing_debug = {
        "query": user_query,
        "intent": classification_dict.get('intent'),
        "entities": (classification_dict.get('intent') or {}).get('entities', []),
        "candidate_tables": (classification_dict.get('routing_plan') or {}).get('candidate_tables', {}),
        "selected_tables": (classification_dict.get('routing_plan') or {}).get('target_tables', []),
        "candidate_collections": (classification_dict.get('routing_plan') or {}).get('candidate_collections', {}),
        "selected_collections": (classification_dict.get('routing_plan') or {}).get('target_collections', []),
        "route": classification.query_type,
        "confidence": classification.confidence
    }
    logger.info(f"[{dataset}] [REQ:{req_id}] [ROUTING_DEBUG] {json.dumps(routing_debug)}")
    
    # Keep standard observability for internal metrics
    observability_payload = {
        "request_id": req_id,
        "total_timing_ms": total_time,
        "generated_sql": None,
        "retrieval_confidence": 0.0,
        "selected_sources": sources
    }
    
    for ex in tool_executions:
        if getattr(ex, 'tool', None) == 'query_structured_data':
            observability_payload["generated_sql"] = getattr(ex, 'query_used', None)
        elif getattr(ex, 'tool', None) == 'search_documents':
            observability_payload["retrieval_confidence"] = getattr(ex, 'average_confidence', 0.0)
            
    logger.info(f"[{dataset}] [REQ:{req_id}] [OBSERVABILITY] {json.dumps(observability_payload)}")
    
    return QueryResponse(
        request_id=req_id,
        answer_context=final_context,
        sources=list(set(sources)),
        trace=trace,
        overall_confidence=classification.confidence,
        warnings=warnings,
        errors=errors
    )
