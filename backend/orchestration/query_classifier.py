"""
Module: query_classifier.py
Purpose: Classifies queries with domain-aware operational intent.
"""

import re
from typing import Dict, Any, List, Optional


def classify_query(query: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Classifies a query into an execution route with deterministic operational mapping.
    """
    query_lower = query.lower().strip()
    history = history or []
    
    # 1. Detect Follow-up context
    is_follow_up = _is_follow_up(query_lower)
    resolved_query = query
    context_reasoning = ""

    if is_follow_up and history:
        last_user_query = next((m['content'] for m in reversed(history) if m['role'] == 'user'), "")
        if last_user_query:
            resolved_query = f"{last_user_query} (Follow-up: {query})"
            context_reasoning = f"Conversational follow-up resolved against: '{last_user_query}'."
            query_lower = resolved_query.lower()

    # 2. Domain-Aware Operational Intent (Deterministic Routing)
    operational_intents = {
        "ingestion_quality": [r"ingestion", r"upload", r"data quality", r"inconsistenc", r"inbound", r"latest upload"],
        "validation_errors": [r"validation", r"rejected", r"failed row", r"error summary", r"invalid", r"rejection"],
        "normalization_activity": [r"normalization", r"mapping", r"transformed", r"standardiz"],
        "anomaly_detection": [r"anomaly", r"spike", r"unusual", r"warning count", r"outlier"],
        "duplicates": [r"duplicate", r"repeated", r"collision"]
    }
    
    detected_domains = [domain for domain, patterns in operational_intents.items() 
                       if any(re.search(p, query_lower) for p in patterns)]

    # 3. Traditional Signal Detection
    sql_explicit = [
        r"how many\b", r"\baverage\b", r"count\b", r"total\b", r"calculate\b", r"top \d+",
        r"spend", r"roi", r"efficiency", r"correlate", r"relationship", r"compare", r"metrics"
    ]
    pdf_explicit = [
        r"policy", r"guideline", r"governance", r"strategy", r"roadmap", r"narrative", r"commentary"
    ]
    
    sql_score = sum(1 for kw in sql_explicit if re.search(kw, query_lower))
    pdf_score = sum(1 for kw in pdf_explicit if re.search(kw, query_lower))
    
    # --- Routing Logic ---
    result = {
        "query_type": "unknown",
        "reasoning": context_reasoning,
        "recommended_tools": [],
        "confidence": 0.0,
        "resolved_query": resolved_query,
        "operational_domain": detected_domains[0] if detected_domains else None
    }

    # Priority 1: Deterministic Operational Routing
    if detected_domains:
        result["query_type"] = "sql"
        result["recommended_tools"] = ["query_structured_data"]
        result["confidence"] = 0.95
        result["reasoning"] = f"Deterministic operational intent detected ({detected_domains[0]}). Routing to structured analytics."
        return result

    # Priority 2: Hybrid/SQL/PDF based on scores
    if sql_score > 0 and pdf_score > 0:
        result["query_type"] = "hybrid"
        result["recommended_tools"] = ["query_structured_data", "search_documents"] if sql_score >= pdf_score else ["search_documents", "query_structured_data"]
        result["confidence"] = 0.85
    elif sql_score > pdf_score:
        result["query_type"] = "sql"
        result["recommended_tools"] = ["query_structured_data"]
        result["confidence"] = 0.90
    elif pdf_score > sql_score:
        result["query_type"] = "pdf"
        result["recommended_tools"] = ["search_documents"]
        result["confidence"] = 0.90
    else:
        # Default to safety with lower confidence
        result["query_type"] = "hybrid"
        result["recommended_tools"] = ["search_documents", "query_structured_data"]
        result["confidence"] = 0.60
        
    return result


def _is_follow_up(query: str) -> bool:
    patterns = [r"^explain ", r"^elaborate", r"^why", r"^how so", r"^expand ", r"^can you explain more"]
    return any(re.match(p, query) for p in patterns)
