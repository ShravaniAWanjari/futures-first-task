import sqlite3
import os
try:
    import chromadb
except ImportError:
    print("ChromaDB not installed. Please install it to verify retrievals.")
    chromadb = None

def verify_retrieval_infrastructure(report_file):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    chroma_dir = os.path.join(base_dir, "chroma")
    
    if chromadb is None:
        report_file.write("ERROR: ChromaDB is not installed.\n")
        return
        
    if not os.path.exists(chroma_dir):
        msg = "ERROR: ChromaDB directory not found.\n"
        print(msg)
        report_file.write(msg)
        return
        
    client = chromadb.PersistentClient(path=chroma_dir)
    
    datasets = ["vistastream", "neonplay"]
    queries = [
        "APAC growth",
        "sci-fi engagement",
        "Europe campaign performance",
        "subtitle quality"
    ]
    
    for dataset in datasets:
        db_path = os.path.join(base_dir, "databases", f"{dataset}.db")
        if not os.path.exists(db_path):
            continue
            
        header = f"=== RETRIEVAL VERIFICATION: {dataset.upper()} ===\n"
        print(header)
        report_file.write(header + "\n")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Verify Chunk and Embedding Counts
        cursor.execute("SELECT COUNT(*) FROM pdf_chunks_metadata")
        sql_chunk_count = cursor.fetchone()[0]
        
        collection_name = f"{dataset}_documents"
        try:
            collection = client.get_collection(name=collection_name)
            chroma_count = collection.count()
        except Exception:
            # Collection might not exist if it's empty or still processing
            chroma_count = 0
            collection = None
            
        report_file.write(f"SQLite Chunk Metadata Count: {sql_chunk_count}\n")
        report_file.write(f"ChromaDB Embedding Count: {chroma_count}\n")
        
        # 2. Collection Integrity Checks
        if sql_chunk_count == chroma_count:
            report_file.write("-> PASS: Chunk metadata count perfectly matches embedding count.\n")
        else:
            report_file.write("-> FAIL: Discrepancy between SQLite chunks and ChromaDB embeddings.\n")
            
        # 3. Detect Missing Embeddings / Orphans / Duplicates
        cursor.execute("SELECT COUNT(*) FROM pdf_chunks_metadata WHERE embedding_id IS NULL")
        missing_embeddings = cursor.fetchone()[0]
        report_file.write(f"SQLite Chunks Missing Embeddings (Orphan Metadata): {missing_embeddings}\n")
        
        cursor.execute("SELECT chunk_id, COUNT(*) FROM pdf_chunks_metadata GROUP BY chunk_id HAVING COUNT(*) > 1")
        dupes = len(cursor.fetchall())
        report_file.write(f"Duplicated Chunk IDs in SQLite: {dupes}\n")
        
        report_file.write("\n--- RETRIEVAL TESTS ---\n")
        
        # 4. Test Retrieval
        if collection is not None and chroma_count > 0:
            for q in queries:
                report_file.write(f"\nQuery: '{q}'\n")
                
                results = collection.query(
                    query_texts=[q],
                    n_results=2
                )
                
                if results['ids'] and results['ids'][0]:
                    for idx, chunk_id in enumerate(results['ids'][0]):
                        distance = results['distances'][0][idx] if 'distances' in results and results['distances'] else "N/A"
                        metadata = results['metadatas'][0][idx]
                        doc_snippet = results['documents'][0][idx][:150].replace('\n', ' ') + "..."
                        
                        source = metadata.get("source_file", "UNKNOWN")
                        page = metadata.get("page_number", "UNKNOWN")
                        section = metadata.get("section_title", "UNKNOWN")
                        
                        report_file.write(f"  Result {idx+1} [Distance: {distance:.4f}]:\n")
                        report_file.write(f"    -> Chunk ID: {chunk_id}\n")
                        report_file.write(f"    -> Source: {source} (Page {page})\n")
                        report_file.write(f"    -> Section: {section}\n")
                        report_file.write(f"    -> Snippet: {doc_snippet}\n")
                        
                        # 5. Metadata Consistency & Traceability
                        cursor.execute("SELECT source_file, page_number FROM pdf_chunks_metadata WHERE chunk_id = ?", (chunk_id,))
                        sql_meta = cursor.fetchone()
                        if sql_meta:
                            # Verify if Chroma metadata correctly maps to SQLite source truth
                            if str(sql_meta[0]) == str(source) and str(sql_meta[1]) == str(page):
                                report_file.write("    -> Traceability Check: PASS (SQLite metadata matches Chroma metadata)\n")
                            else:
                                report_file.write(f"    -> Traceability Check: FAIL (Expected {sql_meta[0]} p{sql_meta[1]}, got {source} p{page})\n")
                        else:
                            report_file.write("    -> Traceability Check: FAIL (Orphan Embedding! No matching row in SQLite)\n")
                else:
                    report_file.write("  No results found.\n")
        else:
            report_file.write("Skipping retrieval tests. Collection empty or not found.\n")
            
        report_file.write("\n" + "="*50 + "\n\n")
        conn.close()

def generate_verification_report():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(base_dir, "retrieval_verification_report.txt")
    
    with open(report_path, "w", encoding="utf-8") as f:
        verify_retrieval_infrastructure(f)
        
    print(f"\nRetrieval verification complete. Audit report generated at: {report_path}")

if __name__ == "__main__":
    generate_verification_report()
