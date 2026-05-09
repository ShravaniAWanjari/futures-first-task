import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.orchestration.query_classifier import classify_query
from backend.orchestration.orchestrator import plan_and_generate_sql
from typing import List, Dict, Any

TEST_CASES = [
    # --- STRUCTURED METRICS: REGION & ROI/SPEND ---
    {
        "query": "Which marketing platforms had the best ROI in North America?",
        "expected_route": "sql",
        "expected_tables": ["marketing_campaigns"],
        "expected_metrics": ["roi"],
        "expected_dimension": "platform",
        "expected_entities": ["North America"]
    },
    {
        "query": "Compare ad-spend efficiency between Europe and APAC.",
        "expected_route": "sql",
        "expected_tables": ["marketing_campaigns"],
        "expected_metrics": ["roi"], # 'efficiency' maps to ROI
        "expected_dimension": None,
        "expected_entities": ["EMEA", "APAC"]
    },
    {
        "query": "Calculate the total marketing spend in LATAM.",
        "expected_route": "sql",
        "expected_tables": ["marketing_campaigns"],
        "expected_metrics": ["spend"],
        "expected_dimension": None,
        "expected_entities": ["LATAM"]
    },
    # --- STRUCTURED METRICS: GROWTH & PERFORMANCE ---
    {
        "query": "Show me the top 5 strongest growth markets.",
        "expected_route": "sql",
        "expected_tables": ["regional_performance"],
        "expected_metrics": ["growth"],
        "expected_dimension": None,
        "expected_entities": []
    },
    {
        "query": "Which regions had the highest watch hour performance metrics?",
        "expected_route": "sql",
        "expected_tables": ["regional_performance"],
        "expected_metrics": ["performance"],
        "expected_dimension": "region",
        "expected_entities": []
    },
    {
        "query": "Compare the performance metrics on TikTok.",
        "expected_route": "sql",
        "expected_tables": ["marketing_campaigns"],
        "expected_metrics": ["performance"],
        "expected_dimension": "platform",
        "expected_entities": []
    },
    # --- PIPELINE/OPERATIONAL METRICS ---
    {
        "query": "Count the data quality inconsistencies found in the latest upload.",
        "expected_route": "sql",
        "expected_tables": ["ingestion_logs"],
        "expected_metrics": None,
        "expected_dimension": None,
        "expected_entities": []
    },
    {
        "query": "Calculate the recent validation errors.",
        "expected_route": "sql",
        "expected_tables": ["validation_summaries"],
        "expected_metrics": None,
        "expected_dimension": None,
        "expected_entities": []
    },
    {
        "query": "How many duplicate warnings were logged?",
        "expected_route": "sql",
        "expected_tables": ["ingestion_logs"],
        "expected_metrics": None,
        "expected_dimension": None,
        "expected_entities": []
    },
    # --- QUALITATIVE / DOCUMENT RETRIEVAL ---
    {
        "query": "What are the primary localization complaints in APAC?",
        "expected_route": "pdf",
        "expected_collections": ["audience_behavior_reports"],
        "expected_metrics": None,
        "expected_dimension": None,
        "expected_entities": ["APAC"]
    },
    {
        "query": "Are there subtitle quality issues in Europe?",
        "expected_route": "pdf",
        "expected_collections": ["audience_behavior_reports"],
        "expected_metrics": None,
        "expected_dimension": None,
        "expected_entities": ["EMEA"]
    },
    {
        "query": "What is the new governance policy for data uploads?",
        "expected_route": "pdf",
        "expected_collections": ["policy_documents"],
        "expected_metrics": None,
        "expected_dimension": None,
        "expected_entities": []
    },
    {
        "query": "Explain the product strategy roadmap for Q3.",
        "expected_route": "pdf",
        "expected_collections": ["strategy_documents"],
        "expected_metrics": None,
        "expected_dimension": None,
        "expected_entities": []
    },
    {
        "query": "Provide a narrative summary of the executive commentary on recent growth.",
        "expected_route": "pdf",
        "expected_collections": ["executive_reports"],
        "expected_metrics": ["growth"],
        "expected_dimension": None,
        "expected_entities": []
    },
    # --- EDGE CASES / FALLBACKS ---
    {
        "query": "What are the engineering roadmap updates?",
        "expected_route": "pdf",
        "expected_collections": ["strategy_documents"],
        "expected_metrics": None,
        "expected_dimension": None,
        "expected_entities": []
    },
    {
        "query": "Compare YouTube vs Instagram spend.",
        "expected_route": "sql",
        "expected_tables": ["marketing_campaigns"],
        "expected_metrics": ["spend"],
        "expected_dimension": "platform",
        "expected_entities": []
    },
    {
        "query": "Give me the total watch hours in LATAM.",
        "expected_route": "sql",
        "expected_tables": ["regional_performance"],
        "expected_metrics": ["performance"],
        "expected_dimension": None,
        "expected_entities": ["LATAM"]
    },
    {
        "query": "Explain the relationship between marketing spend and new subscribers in APAC.",
        "expected_route": "sql",
        "expected_tables": ["marketing_campaigns"], # Spend maps to marketing campaigns
        "expected_metrics": ["spend"],
        "expected_dimension": None,
        "expected_entities": ["APAC"]
    },
    # --- CONVERSATIONAL CONTINUITY (FOLLOW-UPS) ---
    {
        "query": "explain further",
        "is_follow_up": True,
        "history": [
            {"role": "user", "content": "What was the ROI in Europe?"},
            {"role": "assistant", "content": "ROI was high.", "trace": '{"classification": {"query_type": "sql", "recommended_tools": ["query_structured_data"], "intent": {"mode": "structured", "domain": "marketing_performance", "metric": "roi", "entities": ["EMEA"], "confidence": 0.9}, "routing_plan": {"primary_route": "sql", "target_tables": ["marketing_campaigns"], "target_collections": [], "retrieval_strategy": "exact_match"}}}'}
        ],
        "expected_route": "sql",
        "expected_tables": ["marketing_campaigns"],
        "expected_metrics": ["roi"],
        "expected_dimension": None,
        "expected_entities": ["EMEA"]
    },
    {
        "query": "why?",
        "is_follow_up": True,
        "history": [
            {"role": "user", "content": "What are the localization complaints?"},
            {"role": "assistant", "content": "There are many complaints.", "trace": '{"classification": {"query_type": "pdf", "recommended_tools": ["search_documents"], "intent": {"mode": "document", "domain": "localization_quality", "confidence": 0.9}, "routing_plan": {"primary_route": "pdf", "target_tables": [], "target_collections": ["audience_behavior_reports"], "retrieval_strategy": "semantic_search"}}}'}
        ],
        "expected_route": "pdf",
        "expected_collections": ["audience_behavior_reports"],
        "expected_metrics": None,
        "expected_dimension": None,
        "expected_entities": []
    }
]

def run_tests():
    passed = 0
    failed = 0
    
    print("==================================================")
    print("PHASE 9 — ORCHESTRATION REGRESSION SUITE")
    print("==================================================")

    for i, tc in enumerate(TEST_CASES, 1):
        query = tc["query"]
        history = tc.get("history", [])
        
        # 1. Classification
        classification_dict = classify_query(query, history)
        
        # Follow-up inheritance logic (simulating orchestrator logic)
        if tc.get("is_follow_up"):
            import json
            for msg in reversed(history):
                if msg.get('role') == 'assistant' and msg.get('trace'):
                    prev_trace = json.loads(msg['trace'])
                    prev_type = prev_trace['classification']['query_type']
                    classification_dict['query_type'] = prev_type
                    if 'intent' in prev_trace['classification']:
                        classification_dict['intent'] = prev_trace['classification']['intent']
                    if 'routing_plan' in prev_trace['classification']:
                        classification_dict['routing_plan'] = prev_trace['classification']['routing_plan']
                    break
        
        route = classification_dict.get("query_type")
        intent = classification_dict.get("intent", {})
        plan = classification_dict.get("routing_plan", {})
        
        errors = []
        
        # Verify Route
        if route != tc["expected_route"]:
            errors.append(f"Expected route {tc['expected_route']}, got {route}")
            
        # Verify Intent Extraction
        if tc.get("expected_metrics"):
            if intent.get("metric") not in tc["expected_metrics"]:
                errors.append(f"Expected metric {tc['expected_metrics']}, got {intent.get('metric')}")
                
        if tc.get("expected_dimension"):
            if intent.get("dimension") != tc["expected_dimension"]:
                errors.append(f"Expected dimension {tc['expected_dimension']}, got {intent.get('dimension')}")
                
        if tc.get("expected_entities") is not None:
            extracted_entities = intent.get("entities", [])
            for e in tc["expected_entities"]:
                if e not in extracted_entities:
                    errors.append(f"Expected entity {e} missing from {extracted_entities}")

        # Verify Routing Plan
        if tc.get("expected_tables"):
            target_tables = plan.get("target_tables", [])
            if not target_tables or target_tables[0] not in tc["expected_tables"]:
                errors.append(f"Expected tables {tc['expected_tables']}, got {target_tables}")
                
        if tc.get("expected_collections"):
            target_cols = plan.get("target_collections", [])
            if not target_cols or target_cols[0] not in tc["expected_collections"]:
                errors.append(f"Expected collections {tc['expected_collections']}, got {target_cols}")

        if not errors:
            print(f"[PASS] {query}")
            passed += 1
        else:
            print(f"[FAIL] {query}")
            for e in errors:
                print(f"       -> {e}")
            failed += 1

    print("==================================================")
    print(f"RESULTS: {passed} PASSED | {failed} FAILED")
    print("==================================================")
    
if __name__ == "__main__":
    run_tests()
