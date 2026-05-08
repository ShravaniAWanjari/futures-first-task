import requests
import json

BASE_URL = "http://localhost:8000"

def test_api_flow():
    print("1. Creating a new session...")
    resp = requests.post(f"{BASE_URL}/sessions", json={"workspace": "vistastream"})
    session_id = resp.json()["data"]["session_id"]
    print(f"   Created session: {session_id}")
    
    print("\n2. Sending a query...")
    query_payload = {
        "query": "What is the average revenue in APAC?",
        "session_id": session_id,
        "workspace": "vistastream"
    }
    resp = requests.post(f"{BASE_URL}/query", json=query_payload)
    if resp.status_code == 200:
        envelope = resp.json()
        data = envelope["data"]
        print(f"   Response received! (Timing: {data['trace']['total_timing_ms']}ms)")
        print(f"   Answer Context Snippet: {data['answer_context'][:100]}...")
    else:
        print(f"   Error: {resp.text}")
        
    print("\n3. Verifying session persistence...")
    resp = requests.get(f"{BASE_URL}/sessions/{session_id}")
    envelope = resp.json()
    session_data = envelope["data"]
    print(f"   Session Title: {session_data['title']}")
    print(f"   Message count: {len(session_data['messages'])}")
    
    print("\n4. Checking health endpoint...")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"   System Status: {resp.json()['data']['overall_status']}")
    
    print("\n5. Verifying dynamic suggestions...")
    resp = requests.get(f"{BASE_URL}/suggestions?workspace=vistastream")
    print(f"   Suggestions: {resp.json()['data']['suggestions'][0]}...")

if __name__ == "__main__":
    test_api_flow()
