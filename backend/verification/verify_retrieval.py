import sqlite3
import os
import json
import time
from typing import List, Dict, Any
from backend.config import Config

try:
    import chromadb
except ImportError:
    chromadb = None

def load_expectations():
    path = os.path.join(os.path.dirname(__file__), "retrieval_expectations.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_retrieval(query_obj: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Heuristic validation of retrieval against expectations."""
    retrieved_sources = [r['metadata'].get('source_file') for r in results]
    retrieved_text = " ".join([r['document'].lower() for r in results])
    
    # 1. Source Presence
    source_match = any(src in retrieved_sources for src in query_obj['expected_sources'])
    
    # 2. Keyword Overlap
    matched_keywords = [kw for kw in query_obj['expected_keywords'] if kw.lower() in retrieved_text]
    keyword_score = len(matched_keywords) / len(query_obj['expected_keywords'])
    
    # 3. Topic Overlap (Heuristic based on keywords/source)
    topic_match = any(topic.lower() in retrieved_text for topic in query_obj['expected_topics'])
    
    # Determination
    if source_match and keyword_score > 0.5:
        status = "PASS"
        msg = "Expected source found in top retrievals with strong keyword overlap."
    elif source_match or keyword_score > 0.3:
        status = "WARNING"
        msg = "Expected source missing, but significant keyword/topic overlap detected."
    else:
        status = "FAIL"
        msg = "No expected semantic overlap detected."
        
    return {
        "status": status,
        "message": msg,
        "retrieved_sources": list(set(retrieved_sources)),
        "keyword_overlap": len(matched_keywords),
        "source_match": source_match
    }

def verify_retrieval_infrastructure(report_file, expectation_report_file):
    chroma_dir = Config.CHROMA_DB_PATH
    
    if chromadb is None:
        report_file.write("ERROR: ChromaDB is not installed.\n")
        return
        
    if not os.path.exists(chroma_dir):
        msg = "ERROR: ChromaDB directory not found.\n"
        print(msg)
        report_file.write(msg)
        return
        
    client = chromadb.PersistentClient(path=chroma_dir)
    expectations = load_expectations()
    
    summary = {"vistastream": {"pass": 0, "warning": 0, "fail": 0}, "neonplay": {"pass": 0, "warning": 0, "fail": 0}}
    
    expectation_report_file.write("=== RETRIEVAL EXPECTATION VALIDATION REPORT ===\n\n")
    
    datasets = ["vistastream", "neonplay"]
    for dataset in datasets:
        db_path = Config.VISTASTREAM_DB_PATH if dataset == "vistastream" else Config.NEONPLAY_DB_PATH
        if not os.path.exists(db_path):
            continue
            
        header = f"=== RETRIEVAL VERIFICATION: {dataset.upper()} ===\n"
        print(header)
        report_file.write(header + "\n")
        expectation_report_file.write(header + "\n")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Metadata check
        cursor.execute("SELECT COUNT(*) FROM pdf_chunks_metadata")
        sql_chunk_count = cursor.fetchone()[0]
        
        collection_name = f"{dataset}_documents"
        try:
            collection = client.get_collection(name=collection_name)
            chroma_count = collection.count()
        except Exception:
            chroma_count = 0
            collection = None
            
        report_file.write(f"SQLite Chunk Metadata Count: {sql_chunk_count}\n")
        report_file.write(f"ChromaDB Embedding Count: {chroma_count}\n")
        
        # Expectations validation
        dataset_expectations = [e for e in expectations if e['environment'] == dataset]
        for exp in dataset_expectations:
            print(f"Testing Query: '{exp['query']}'...")
            expectation_report_file.write(f"Query: {exp['query']}\n")
            
            if collection and chroma_count > 0:
                results = collection.query(query_texts=[exp['query']], n_results=3)
                formatted_results = []
                if results['ids'] and results['ids'][0]:
                    for i in range(len(results['ids'][0])):
                        formatted_results.append({
                            "id": results['ids'][0][i],
                            "document": results['documents'][0][i],
                            "metadata": results['metadatas'][0][i]
                        })
                
                validation = validate_retrieval(exp, formatted_results)
                status = validation['status']
                summary[dataset][status.lower()] += 1
                
                expectation_report_file.write(f"Status: [{status}] {validation['message']}\n")
                expectation_report_file.write(f"Retrieved Sources: {', '.join(validation['retrieved_sources'])}\n")
                expectation_report_file.write(f"Keyword Overlap: {validation['keyword_overlap']}\n")
                if formatted_results:
                    expectation_report_file.write(f"Snippet Preview: {formatted_results[0]['document'][:150].replace('\\n', ' ')}...\n")
            else:
                expectation_report_file.write("Status: [FAIL] Collection empty or missing.\n")
                summary[dataset]["fail"] += 1
            
            expectation_report_file.write("-" * 40 + "\n")
            
        report_file.write("\n" + "="*50 + "\n\n")
        conn.close()

    # Final Summary in Expectation Report
    expectation_report_file.write("\n=== RETRIEVAL EXPECTATION SUMMARY ===\n")
    for ds in datasets:
        ds_sum = summary[ds]
        total = ds_sum['pass'] + ds_sum['warning'] + ds_sum['fail']
        expectation_report_file.write(f"{ds.upper()}: Total: {total} | PASS: {ds_sum['pass']} | WARNING: {ds_sum['warning']} | FAIL: {ds_sum['fail']}\n")

def generate_verification_report():
    report_path = os.path.join(Config.BASE_DIR, "docs", "reports", "retrieval_verification_report.txt")
    expectation_report_path = os.path.join(Config.BASE_DIR, "docs", "reports", "retrieval_expectation_report.txt")
    
    with open(report_path, "w", encoding="utf-8") as f, open(expectation_report_path, "w", encoding="utf-8") as exp_f:
        verify_retrieval_infrastructure(f, exp_f)
        
    print(f"\nRetrieval verification complete.")
    print(f"Technical Audit: {report_path}")
    print(f"Expectation Report: {expectation_report_path}")

if __name__ == "__main__":
    generate_verification_report()
