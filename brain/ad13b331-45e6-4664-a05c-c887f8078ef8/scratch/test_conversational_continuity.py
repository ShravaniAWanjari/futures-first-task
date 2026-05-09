import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from backend.orchestration.orchestrator import orchestrate_query
from backend.schemas import QueryRequest

def test_conversational_continuity():
    # 1. Establish initial context (SQL)
    print("\n" + "="*50)
    print("STEP 1: Initial Operational Query")
    print("="*50)
    q1 = "Why are there so many warnings in the watch activity data?"
    req1 = QueryRequest(query=q1, dataset="neonplay")
    res1 = orchestrate_query(req1)
    
    # Mock history for the follow-up
    history = [
        {"role": "user", "content": q1},
        {"role": "assistant", "content": res1.answer_context, "trace": res1.trace.model_dump_json() if res1.trace else None}
    ]
    
    # 2. Test VALID FOLLOW-UP
    print("\n" + "="*50)
    print("STEP 2: Valid Follow-up (Expected: Inheritance)")
    print("="*50)
    q2 = "explain further"
    req2 = QueryRequest(query=q2, dataset="neonplay")
    res2 = orchestrate_query(req2, history=history)
    
    # 3. Test VALID NEW TOPIC
    print("\n" + "="*50)
    print("STEP 3: Valid New Topic (Expected: Fresh Orchestration)")
    print("="*50)
    q3 = "what is watch activity data?"
    req3 = QueryRequest(query=q3, dataset="neonplay")
    res3 = orchestrate_query(req3, history=history)
    
    # 4. Test VALID NEW TOPIC (Another one)
    print("\n" + "="*50)
    print("STEP 4: Another New Topic (Expected: Fresh Orchestration)")
    print("="*50)
    q4 = "what are localization complaints?"
    req4 = QueryRequest(query=q4, dataset="neonplay")
    res4 = orchestrate_query(req4, history=history)

if __name__ == "__main__":
    test_conversational_continuity()
