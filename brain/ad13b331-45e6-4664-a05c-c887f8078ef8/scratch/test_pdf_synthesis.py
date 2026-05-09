import json
import sys
import os

# Set output to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from backend.orchestration.orchestrator import orchestrate_query
from backend.api.services.response_synthesizer import synthesize_response
from backend.schemas import QueryRequest

def test_synthesis():
    q = "What is the current status of subtitle quality improvements?"
    request = QueryRequest(query=q, dataset="neonplay")
    response = orchestrate_query(request)
    
    synthesized = synthesize_response(
        answer_context=response.answer_context,
        sources=response.sources,
        confidence=response.overall_confidence,
        original_query=q
    )
    
    print(f"\n--- SYNTHESIZED RESPONSE ---\n{synthesized}")

if __name__ == "__main__":
    test_synthesis()
