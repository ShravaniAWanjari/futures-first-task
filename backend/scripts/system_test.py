import sys
import io
import os
import json
from pathlib import Path

# Fix Windows encoding issues for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.api.services.query_service import QueryService
from backend.api import session_manager

def run_test_query(query, session_id="test_session", workspace="vistastream"):
    print(f"\n--- TESTING QUERY: {query} ---")
    try:
        # Create a new session for EACH query to test title generation correctly
        session_info = session_manager.create_session(workspace=workspace)
        session_id = session_info["session_id"]
        
        response = QueryService.execute_query(
            query=query,
            session_id=session_id,
            workspace=workspace,
            request_id="test_req"
        )
        print(f"TITLE: {session_manager.get_session(session_id).get('title', 'N/A')}")
        print(f"TRACE:\n{response.raw_reasoning}")
        print(f"ANSWER:\n{response.answer_context}")
        if response.structured_data:
            print(f"STRUCTURED DATA FOUND: {list(response.structured_data.keys())}")
        else:
            print("NO STRUCTURED DATA.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Init sessions
    session_manager.init_sessions_db()
    
    test_queries = [
        "Which region had the lowest spend?",
        "What regions did we cover",
        "Which platform had the highest ROI in North America?",
        "What was the subscriber growth in APAC during Q2?",
        "Compare spend between Europe and LATAM.",
        "What are the common viewer complaints in the recent report?",
        "What is LATAM"
    ]
    
    for q in test_queries:
        run_test_query(q)
