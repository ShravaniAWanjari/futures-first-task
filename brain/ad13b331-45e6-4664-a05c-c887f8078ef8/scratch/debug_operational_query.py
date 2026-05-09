import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from backend.orchestration.orchestrator import orchestrate_query
from backend.api.services.response_synthesizer import synthesize_response
from backend.schemas import QueryRequest

def test_queries():
    queries = [
        "Why are there so many warnings in the watch activity data?",
        "List the data quality inconsistencies found in the latest upload.",
        "How many duplicate warnings were logged?",
        "Explain the recent validation failures."
    ]
    
    for q in queries:
        print(f"\n" + "="*50)
        print(f"QUERY: {q}")
        print("="*50)
        
        request = QueryRequest(query=q, dataset="neonplay")
        response = orchestrate_query(request)
        
        print(f"--- RAW CONTEXT ---\n{response.answer_context}")
        
        synthesized = synthesize_response(
            answer_context=response.answer_context,
            sources=response.sources,
            confidence=response.overall_confidence,
            original_query=q
        )
        
        print(f"\n--- SYNTHESIZED RESPONSE ---\n{synthesized}")

if __name__ == "__main__":
    test_queries()
