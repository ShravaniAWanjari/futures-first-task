import re
import json
from typing import Dict, Any

def classify_query(query: str) -> Dict[str, Any]:
    """
    Classifies an incoming management query into 'sql', 'pdf', or 'hybrid' execution routes.
    Employs NLP heuristics to determine quantitative vs qualitative intent.
    Provides orchestration systems with specific tool recommendations and a confidence score.
    """
    query_lower = query.lower()
    
    # 1. Define heuristic intent clusters
    sql_keywords = [
        r"how many", r"average", r"\bavg\b", r"count", r"metric", r"trend", 
        r"total", r"sum", r"revenue", r"watch hours", r"subscribers", 
        r"churn", r"performance", r"monthly", r"quarterly", r"q[1-4]",
        r"completion rate", r"top \d+", r"distribution", r"calculate"
    ]
    
    pdf_keywords = [
        r"policy", r"governance", r"roadmap", r"executive", r"commentary",
        r"strategy", r"guidelines", r"report", r"explain", r"why did", 
        r"context", r"narrative", r"decision matrix", r"logs", r"timeline",
        r"document", r"paragraph", r"section"
    ]
    
    hybrid_keywords = [
        r"compare.*report", r"correlate", r"explain inconsistency", 
        r"explain drop", r"why is revenue", r"compare.*data", 
        r"impact on metrics", r"does the report match", r"match.*metrics"
    ]
    
    # 2. Score the query intent
    sql_score = sum(1 for kw in sql_keywords if re.search(kw, query_lower))
    pdf_score = sum(1 for kw in pdf_keywords if re.search(kw, query_lower))
    hybrid_score = sum(1 for kw in hybrid_keywords if re.search(kw, query_lower))
    
    # 3. Formulate the response
    result = {
        "query_type": "unknown",
        "reasoning": "",
        "recommended_tools": [],
        "confidence": 0.0
    }
    
    # Hybrid triggers explicitly via distinct keywords OR overlapping strong signals
    is_hybrid = hybrid_score > 0 or (sql_score >= 1 and pdf_score >= 1)
    
    if is_hybrid:
        result["query_type"] = "hybrid"
        result["reasoning"] = "Query contains overlapping requests requiring both quantitative analytics and qualitative document context."
        result["recommended_tools"] = ["query_structured_data", "search_documents"]
        
        # Calculate algorithmic confidence based on overlapping signal strength
        base_confidence = 0.70 + (min(sql_score + pdf_score + hybrid_score, 5) * 0.05)
        result["confidence"] = round(min(base_confidence, 0.98), 2)
        
    elif sql_score > pdf_score:
        result["query_type"] = "sql"
        result["reasoning"] = "Query strongly focuses on structured quantitative metrics, counts, averages, or database trends."
        result["recommended_tools"] = ["query_structured_data"]
        
        base_confidence = 0.75 + (min(sql_score, 5) * 0.05)
        result["confidence"] = round(min(base_confidence, 0.99), 2)
        
    elif pdf_score > sql_score:
        result["query_type"] = "pdf"
        result["reasoning"] = "Query targets unstructured qualitative data such as policy, strategy documentation, or executive narrative."
        result["recommended_tools"] = ["search_documents"]
        
        base_confidence = 0.75 + (min(pdf_score, 5) * 0.05)
        result["confidence"] = round(min(base_confidence, 0.99), 2)
        
    else:
        # Fallback for ambiguous or overly brief queries
        result["query_type"] = "hybrid"
        result["reasoning"] = "Query intent is ambiguous or lacks dominant signal. Defaulting to broad multi-tool search."
        result["recommended_tools"] = ["query_structured_data", "search_documents"]
        result["confidence"] = 0.50

    return result

if __name__ == "__main__":
    # Test suite for the orchestration layer
    test_queries = [
        "What was the total revenue in APAC last quarter?",
        "What does the Q2 executive report say about our European expansion strategy?",
        "Why did our watch hours drop in Q3, and does the executive report explain it?",
        "Show me the top 10 movies by completion rate.",
        "What are the official guidelines for handling malformed CSV uploads?",
        "Hello!"
    ]
    
    print("=== QUERY CLASSIFIER ROUTING TESTS ===\n")
    for q in test_queries:
        print(f"Incoming Query: '{q}'")
        res = classify_query(q)
        print(json.dumps(res, indent=2))
        print("-" * 60)
