"""
Module: query_classifier.py
Purpose: Classifies queries with domain-aware operational intent.
"""

import re
from typing import Dict, Any, List, Optional


# Phase 7: Small Talk Responses (never trigger retrieval)
SMALL_TALK_RESPONSES = {
    "greeting": "Hello! I'm your operational intelligence assistant for this workspace. You can ask me about data quality, marketing performance, regional metrics, content strategy, or any of the uploaded reports. What would you like to explore?",
    "acknowledgement": "You're welcome! Let me know if there's anything else you'd like to analyze.",
    "capability": "I can help you with:\n\n* **Data Analysis** — query structured databases for metrics, trends, and comparisons\n* **Document Intelligence** — search uploaded PDFs for strategy, policy, and operational insights\n* **Operational Diagnostics** — analyze ingestion logs, warnings, and data quality issues\n\nJust ask a question in plain language!",
    "farewell": "Goodbye! Feel free to return anytime you need operational insights."
}

def _is_small_talk(query: str) -> Optional[str]:
    """Phase 7: Detects conversational small talk that should NOT trigger retrieval."""
    q = query.lower().strip()
    
    greetings = [r"^(?:hi|hello|hey|good morning|good afternoon|good evening|greetings)\b", r"^how are you", r"^how are things"]
    acknowledgements = [r"^(?:thanks|thank you|thx|cheers|appreciated|great)", r"^(?:ok|okay|got it|understood|cool|nice)$"]
    capabilities = [r"what can you do", r"what are you", r"help me", r"how do you work", r"what do you know", r"what are your capabilities"]
    farewells = [r"^(?:bye|goodbye|see you|later|exit|quit)$"]
    
    if any(re.search(p, q) for p in greetings): return "greeting"
    if any(re.search(p, q) for p in acknowledgements): return "acknowledgement"
    if any(re.search(p, q) for p in capabilities): return "capability"
    if any(re.search(p, q) for p in farewells): return "farewell"
    return None

def _classify_conversational_action(query: str) -> Optional[str]:
    """Part2-Phase1: Classifies conversational actions that reuse existing context."""
    q = query.lower().strip()
    
    formatting = [r"structure.*better", r"use bullet", r"format.*better", r"make.*concise", r"clean.*up", r"organize", r"bullet\s*point"]
    clarification = [r"what do you mean", r"what is", r"what are", r"define", r"explain\s+\w+"]
    continuation = [r"^continue$", r"^go on$", r"^what else", r"^more$", r"^and\?$"]
    refinement = [r"shorter version", r"executive summary", r"more detail", r"briefly", r"summarize"]
    
    if any(re.search(p, q) for p in formatting): return "formatting_request"
    if any(re.search(p, q) for p in clarification): return "clarification_request"
    if any(re.search(p, q) for p in continuation): return "continuation_request"
    if any(re.search(p, q) for p in refinement): return "refinement_request"
    return None


def classify_query(query: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Classifies a query into an execution route with deterministic operational mapping.
    """
    query_lower = query.lower().strip()
    history = history or []
    
    # Phase 7: Small Talk Detection (BEFORE any routing)
    small_talk_type = _is_small_talk(query_lower)
    if small_talk_type:
        return {
            "query_type": "conversational",
            "reasoning": f"Small talk detected: {small_talk_type}",
            "recommended_tools": [],
            "confidence": 1.0,
            "resolved_query": query,
            "operational_domain": None,
            "intent": None,
            "routing_plan": None,
            "follow_up_detected": False,
            "conversational_response": SMALL_TALK_RESPONSES.get(small_talk_type, "How can I help you?"),
            "conversational_action": None
        }
    
    # Part2-Phase1: Conversational Action Classification
    conv_action = _classify_conversational_action(query_lower)
    
    # 1. Detect Follow-up context
    is_follow_up = _is_follow_up(query_lower) or conv_action in [
        "continuation_request",
        "formatting_request",
        "refinement_request",
        "clarification_request",
    ]
    resolved_query = query
    context_reasoning = ""

    if is_follow_up and history:
        # Resolve against the previous user turn (not the current incoming query).
        last_user_query = next(
            (
                m['content']
                for m in reversed(history)
                if m.get('role') == 'user' and str(m.get('content', '')).strip().lower() != query.strip().lower()
            ),
            ""
        )
        if last_user_query:
            resolved_query = f"{last_user_query} (Follow-up: {query})"
            context_reasoning = f"Conversational follow-up resolved against: '{last_user_query}'."
            query_lower = resolved_query.lower()

    # 1.5 Domain Restriction Layer (Phase 9: Intent-Aware)
    if _is_restricted(query_lower):
        return {
            "query_type": "blocked",
            "reasoning": "Query violates operational domain boundaries.",
            "recommended_tools": [],
            "confidence": 1.0,
            "resolved_query": resolved_query,
            "operational_domain": None,
            "intent": None,
            "routing_plan": None
        }

    # 2. Domain-Aware Operational Intent (Deterministic Routing)
    operational_intents = {
        "duplicates": [r"duplicate", r"duplicates", r"repeated", r"collision"],
        "validation_errors": [r"validation", r"validation error", r"rejected", r"failed row", r"error summary", r"invalid", r"rejection", r"malformed"],
        "ingestion_quality": [r"ingestion", r"upload", r"upload issue", r"pipeline", r"data quality", r"inconsistenc", r"inbound", r"latest upload"],
        "normalization_activity": [r"normalization", r"mapping", r"transformed", r"standardiz"],
        "anomaly_detection": [r"anomaly", r"spike", r"unusual", r"warning", r"warnings", r"warning count", r"outlier"],
        # PDF DOMAINS
        "localization_quality": [r"localization", r"subtitle", r"complaint", r"feedback"],
        "policy_and_governance": [r"policy", r"governance", r"guideline", r"compliance"],
        "product_strategy": [r"roadmap", r"strategy", r"vision", r"planning"],
        "executive_commentary": [r"commentary", r"executive", r"summary report"]
    }
    
    detected_domains = [domain for domain, patterns in operational_intents.items() 
                       if any(re.search(p, query_lower) for p in patterns)]

    # 3. Traditional Signal Detection
    sql_explicit = [
        r"how many\b", r"\baverage\b", r"count\b", r"total\b", r"calculate\b", r"top \d+",
        r"spend", r"roi", r"efficiency", r"correlate", r"relationship", r"compare", r"metrics", 
        r"\bshow\b", r"\blist\b", r"region", r"country", r"coverage", r"platform", r"broken down"
    ]
    pdf_explicit = [
        r"policy", r"guideline", r"governance", r"strategy", r"roadmap", r"narrative", r"commentary"
    ]
    narrative_signals = [
        "explain", "summary", "summarize", "commentary", "roadmap", "strategy", 
        "policy", "governance", "guidelines", "narrative", "recommendation", "risk", "outlook"
    ]
    
    sql_score = sum(1 for kw in sql_explicit if re.search(kw, query_lower))
    pdf_score = sum(1 for kw in pdf_explicit if re.search(kw, query_lower))
    narrative_intent = any(kw in query_lower for kw in narrative_signals)

    # Narrative weighting (Phase 5): Suppress SQL if narrative signal is strong
    # Exception: do not suppress if explicit analytical relationship/comparison terms are present
    analytical_exceptions = [r"\brelationship\b", r"\bcorrelation\b", r"\bvs\b", r"\bversus\b", r"\bcompare\b"]
    is_analytical_exception = any(re.search(kw, query_lower) for kw in analytical_exceptions)
    
    if narrative_intent and not is_analytical_exception:
        sql_score = 0
        pdf_score += 2 # Boost PDF
    
    # --- Routing Logic ---
    result = {
        "query_type": "unknown",
        "reasoning": context_reasoning,
        "recommended_tools": [],
        "confidence": 0.0,
        "resolved_query": resolved_query,
        "operational_domain": detected_domains[0] if detected_domains else None,
        "follow_up_detected": is_follow_up,
        "conversational_action": conv_action
    }

    # Priority 1: Deterministic Operational Routing
    if detected_domains:
        pdf_domains = ["localization_quality", "policy_and_governance", "product_strategy", "executive_commentary"]
        # Favor PDF if any detected domain is a PDF domain
        target_domain = next((d for d in detected_domains if d in pdf_domains), detected_domains[0])
        
        if target_domain in pdf_domains:
            result["query_type"] = "pdf"
            result["recommended_tools"] = ["search_documents"]
            result["reasoning"] = f"Deterministic document intent detected ({target_domain}). Routing to semantic retrieval."
        else:
            result["query_type"] = "sql"
            result["recommended_tools"] = ["query_structured_data"]
            result["reasoning"] = f"Deterministic operational intent detected ({target_domain}). Routing to structured analytics."
        
        result["confidence"] = 0.95
        result["operational_domain"] = target_domain
    
    # Priority 2: Strict Single-Route selection (only if not already set by domain)
    elif sql_score > pdf_score:
        result["query_type"] = "sql"
        result["recommended_tools"] = ["query_structured_data"]
        result["confidence"] = 0.90
        result["reasoning"] += " Strong structured analytics signal detected."
    elif pdf_score > 0: # Favor PDF if any signal exists after SQL suppression
        result["query_type"] = "pdf"
        result["recommended_tools"] = ["search_documents"]
        result["confidence"] = 0.90
        result["reasoning"] += " Narrative or document analysis signal detected."
    elif sql_score > 0 and sql_score == pdf_score:
        # Tie breaker - favor structured analytics if explicitly requested
        result["query_type"] = "sql"
        result["recommended_tools"] = ["query_structured_data"]
        result["confidence"] = 0.70
        result["reasoning"] += " Mixed signals detected. Defaulting to structured analytics tie-breaker."
    else:
        # Default fallback - safest single route for general questions
        result["query_type"] = "pdf"
        result["recommended_tools"] = ["search_documents"]
        result["confidence"] = 0.60
        result["reasoning"] += " Weak signals detected. Defaulting to document retrieval fallback."
        
    # 4. Structured Intent Extraction
    result["intent"] = _extract_intent(query_lower, result["query_type"], detected_domains)
    
    # 5. Deterministic Routing Plan
    result["routing_plan"] = _plan_routing(result["intent"], query_lower)
        
    return result


def _plan_routing(intent: Optional[Dict[str, Any]], query_lower: str = "") -> Dict[str, Any]:
    """
    Creates a deterministic routing plan based on structured intent.
    Maps operational domains directly to schema objects or collections using scoring.
    """
    if not intent:
        return {
            "primary_route": "pdf",
            "target_tables": [],
            "target_collections": ["general_documents"],
            "retrieval_strategy": "semantic_fallback"
        }

    domain = intent.get("domain", "")
    mode = intent.get("mode", "document")
    metric = intent.get("metric")
    dimension = intent.get("dimension")

    plan = {
        "primary_route": "sql" if mode == "structured" else "pdf",
        "target_tables": [],
        "target_collections": [],
        "retrieval_strategy": "exact_match" if mode == "structured" else "semantic_search"
    }

    if mode == "structured":
        # ... (Table selection scoring) ...
        # ...
        # ... Selection
        threshold = 0.6
        scores = {
            "ingestion_logs": 0.0,
            "validation_summaries": 0.0,
            "marketing_campaigns": 0.0,
            "regional_performance": 0.0
        }
        
        if domain in ["ingestion_quality", "duplicates", "anomaly_detection"]:
            scores["ingestion_logs"] += 0.9
        if domain == "validation_errors":
            scores["validation_summaries"] += 0.9
            
        if metric in ["roi", "spend"]:
            scores["marketing_campaigns"] += 0.7
        if metric == "growth":
            scores["regional_performance"] += 0.8
            
        if metric == "performance":
            if dimension == "platform":
                scores["marketing_campaigns"] += 0.7
            elif dimension == "region":
                scores["regional_performance"] += 0.7
            else:
                scores["regional_performance"] += 0.5
                scores["marketing_campaigns"] += 0.5
                
        # Dimension boosting
        if dimension == "platform":
            scores["marketing_campaigns"] += 0.3
        elif dimension == "region":
            scores["regional_performance"] += 0.3
            
        plan["candidate_tables"] = scores
        plan["target_tables"] = [table for table, score in scores.items() if score >= threshold]

        # Fallback if empty
        if not plan["target_tables"]:
            if domain == "marketing_performance":
                plan["target_tables"] = ["marketing_campaigns"]
            else:
                plan["target_tables"] = ["regional_performance"]
                
    else:
        # Map Document Collections deterministically
        col_scores = {
            "audience_behavior_reports": 0.0,
            "policy_documents": 0.0,
            "strategy_documents": 0.0,
            "executive_reports": 0.0,
            "operational_reports": 0.0
        }
        
        if domain == "localization_quality" or "subtitle" in str(dimension) or "complaint" in query_lower:
            col_scores["audience_behavior_reports"] = 1.0
        elif domain == "policy_and_governance" or "policy" in query_lower or "governance" in query_lower:
            col_scores["policy_documents"] = 1.0
        elif domain == "product_strategy" or "roadmap" in query_lower or "strategy" in query_lower:
            col_scores["strategy_documents"] = 1.0
        elif domain == "executive_commentary" or "executive" in query_lower:
            col_scores["executive_reports"] = 1.0
        else:
            col_scores["operational_reports"] = 0.5 # default weak signal
            
        plan["candidate_collections"] = col_scores
        plan["target_collections"] = [c for c, s in col_scores.items() if s >= 0.5]

    return plan


def _extract_intent(query: str, query_type: str, detected_domains: List[str]) -> Optional[Dict[str, Any]]:
    """
    Extracts structured analytical intent from the user query.
    """
    intent = {
        "mode": "structured" if query_type == "sql" else "document",
        "domain": detected_domains[0] if detected_domains else ("marketing_performance" if query_type == "sql" else "operational_reports"),
        "metric": None,
        "dimension": None,
        "extreme": None, # highest, lowest
        "entities": [],
        "confidence": 0.90 if query_type == "sql" else 0.85
    }
    
    # Extract Extremes (Phase 16)
    if any(k in query for k in ["highest", "most", "top", "best", "greatest", "max"]):
        intent["extreme"] = "highest"
    elif any(k in query for k in ["lowest", "least", "bottom", "worst", "min"]):
        intent["extreme"] = "lowest"
    
    # Extract Metrics
    metrics_map = {
        "roi": ["roi", "efficiency", "return"],
        "spend": ["spend", "cost", "budget"],
        "growth": ["growth", "subscriber", "new_subscriber"],
        "performance": ["performance", "watch hours", "completion", "engagement"]
    }
    for m, keywords in metrics_map.items():
        if any(kw in query for kw in keywords):
            intent["metric"] = m
            break
            
    # Extract Dimensions
    dimensions_map = {
        "platform": ["platform", "channel", "youtube", "tiktok", "instagram", "tv"],
        "region": ["region", "europe", "apac", "na", "north america", "latam", "emerging market"]
    }
    for d, keywords in dimensions_map.items():
        if any(kw in query for kw in keywords):
            intent["dimension"] = d
            break
            
    # Extract Entities (Mock basic NER with Normalization)
    entities = []
    
    # Regions
    if any(kw in query for kw in ["apac", "asia pacific", "asia-pacific"]): entities.append("APAC")
    if any(kw in query for kw in ["latam", "latin america"]): entities.append("LATAM")
    if any(kw in query for kw in ["europe", "emea", "middle east", "africa"]): entities.append("EMEA")
    if "north america" in query or re.search(r"\bna\b", query): entities.append("North America")
        
    # Platforms
    platforms = {
        "youtube": "YouTube Shorts", "youtube shorts": "YouTube Shorts",
        "tiktok": "TikTok", "tik tok": "TikTok",
        "instagram": "Instagram Reels", "reels": "Instagram Reels",
        "tv": "Connected TV", "connected tv": "Connected TV",
        "google": "Google Ads", "google ads": "Google Ads"
    }
    for kw, entity in platforms.items():
        if kw in query:
            entities.append(entity)
            
    # Operational Topics (Fuzzy extraction for SQL LIKE filters)
    topics = ["watch activity", "marketing", "validation", "ingestion", "subtitle", "localization"]
    for topic in topics:
        if topic in query:
            entities.append(topic)

    # Time Periods (Quarters, Fiscal Years)
    quarters = {
        "q1": "Q1", "quarter 1": "Q1",
        "q2": "Q2", "quarter 2": "Q2",
        "q3": "Q3", "quarter 3": "Q3",
        "q4": "Q4", "quarter 4": "Q4",
        "fy2026": "FY2026", "2026": "FY2026",
        "fy2025": "FY2025", "2025": "FY2025"
    }
    for kw, entity in quarters.items():
        if kw in query:
            entities.append(entity)
    
    if entities:
        # De-duplicate
        intent["entities"] = list(set(entities))
        
    return intent


def _is_restricted(query: str) -> bool:
    """Phase 9: Intent-aware domain gating. Only blocks actual code generation / exploits."""
    restricted_patterns = [
        # Coding generation — requires code-specific target after verb
        r"\b(?:write|generate|create)\s+(?:a\s+)?(?:code|script|python|javascript|html|css|sql snippet|program|function|class)\b",
        r"\b(?:def|class|function)\s+\w+\(",
        
        # Explicit / inappropriate
        r"\b(?:fuck|shit|bitch|asshole|cunt|dick)\b",
        
        # Unrelated tutoring
        r"\b(?:teach me|how do i learn|tutor me in)\b",
        
        # Roleplay / Jailbreaks
        r"\b(?:pretend to be|act as|ignore previous instructions|you are now)\b"
    ]
    return any(re.search(p, query) for p in restricted_patterns)


def _is_follow_up(query: str) -> bool:
    """Detects if a query is a true conversational follow-up or a new topic."""
    q = query.lower().strip()
    
    # 1. Explicit Follow-up Patterns
    follow_up_patterns = [
        r"^explain (?:further|more|that|this)\b",
        r"^provide more\b",
        r"^tell me more\b",
        r"^any other\b",
        r"^why\??$",
        r"^how so\??$",
        r"^expand on (?:this|that)\b",
        r"^drill (?:deeper|down)\b",
        r"^what caused (?:this|that)\b",
        r"^compare (?:that|this)\b",
        r"^was this worse before\b",
        r"^summarize (?:that|it|this)\b",
        r"^can you summarize\b",
        r"^elaborate\b",
        r"^(?:show|list|only|just|specifically|give|provide)\b",
        r"\bbullet\b",
        r"\bpoints\b"
    ]
    
    # 2. Structural Indicators (pronouns, ellipsis, short dependent phrasing)
    structural_indicators = [
        r"\b(?:that|this|it|those|these)\??$",
        r"^\.\.\.",
        r"^(?:more|details|why|how)\??$"
    ]
    
    is_explicit = any(re.match(p, q) for p in follow_up_patterns)
    is_structural = any(re.match(p, q) for p in structural_indicators)
    
    if is_explicit or is_structural:
        # Strong Follow-up Override: "Provide more" should always follow up
        strong_follow_up = any(re.match(p, q) for p in [r"^provide more\b", r"^tell me more\b", r"^any other\b", r"^what else\b"])
        
        if not strong_follow_up:
            # Topic Rejection: Even if it looks like a follow-up, 
            # if it contains a clear operational topic, treat as a new query.
            topic_indicators = [
                r"watch activity", r"marketing", r"regional", r"governance", 
                r"roadmap", r"ingestion", r"subtitle", r"localization",
                r"roi", r"spend", r"metrics", r"performance", r"acquisitions", r"growth"
            ]
            if any(re.search(p, q) for p in topic_indicators):
                return False
        return True
        
    return False
