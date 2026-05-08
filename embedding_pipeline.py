"""
Module: embedding_pipeline.py
Purpose: Initializes ChromaDB embeddings and bridges the semantic layout back to SQLite.
Responsibilities: Chroma client initialization, upsert batching, and dual-system synchronization.
Security Boundaries: Utilizes dedicated collection namespaces to strictly prevent Startup and Enterprise semantic cross-contamination.
Key Decisions: Utilizes a dynamic two-step commit to ensure the relational DB `embedding_id` perfectly matches the finalized Chroma state.
Inputs: SQLite connection, parsed chunk payloads.
Outputs: Persistent vector collections and SQLite relation updates.
"""

import os
import sqlite3
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("ChromaDB not installed. Please run: pip install chromadb")
    chromadb = None

from logging_utils import get_file_logger

def get_chroma_client():
    """
    Initializes a persistent ChromaDB client mapped to our local chroma directory.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    chroma_dir = os.path.join(base_dir, "chroma")
    os.makedirs(chroma_dir, exist_ok=True)
    
    if chromadb is None:
        return None
        
    return chromadb.PersistentClient(path=chroma_dir)

def embed_chunks(sqlite_conn, dataset_name, chunks):
    """
    Embeds chunks into ChromaDB and links the embedding_id back to SQLite.
    Provides strict isolation between environments by utilizing dedicated collections.
    """
    if chromadb is None:
        return {"status": "error", "message": "ChromaDB is not installed."}
        
    logger = get_file_logger(dataset_name)
    client = get_chroma_client()
    
    # 1. Create separate collections for strict environment isolation
    collection_name = f"{dataset_name}_documents"
    collection = client.get_or_create_collection(name=collection_name)
    
    docs_to_embed = []
    metadatas = []
    ids = []
    
    created = 0
    failed = 0
    
    # 2. Extract and format metadata requirements
    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        try:
            ids.append(chunk_id)
            docs_to_embed.append(chunk["chunk_text"])
            
            # ChromaDB metadata must be primitive types (str, int, float, bool)
            metadatas.append({
                "chunk_id": chunk_id,
                "source_file": str(chunk["source_file"]),
                "page_number": int(chunk["page_number"]),
                "section_title": str(chunk["section_title"])
            })
        except Exception as e:
            failed += 1
            logger.error(f"[{dataset_name}] [embed] Failed to parse metadata for chunk {chunk_id}: {e}")
            
    if ids:
        try:
            # 3. Upsert to persist embeddings locally and prevent duplication
            collection.upsert(
                documents=docs_to_embed,
                metadatas=metadatas,
                ids=ids
            )
            created = len(ids)
            
            # 4. Update pdf_chunks_metadata.embedding_id in SQLite
            cursor = sqlite_conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            # We map Chroma's intrinsic ID to SQLite's embedding_id parameter
            update_data = [(cid, cid) for cid in ids]
            cursor.executemany("""
                UPDATE pdf_chunks_metadata 
                SET embedding_id = ? 
                WHERE chunk_id = ?
            """, update_data)
            
            sqlite_conn.commit()
            logger.info(f"[{dataset_name}] [embed] Successfully embedded and linked {created} chunks in DB.")
            
        except Exception as e:
            logger.error(f"[{dataset_name}] [embed] Failed batch embedding transaction: {e}")
            failed += len(ids)
            created = 0
            
    # 5. Log collection counts
    count = collection.count()
    logger.info(f"[{dataset_name}] [embed] Collection '{collection_name}' currently holds {count} semantic embeddings.")
    
    return {
        "created": created,
        "failed": failed,
        "total_in_collection": count
    }

if __name__ == "__main__":
    # Test script: Fetch the chunks currently sitting un-embedded in SQLite and embed them
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    def process_existing_chunks(dataset_name):
        db_path = os.path.join(base_dir, "databases", f"{dataset_name}.db")
        if not os.path.exists(db_path):
            print(f"Skipping {dataset_name}, DB not found.")
            return
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT chunk_id, source_file, page_number, section_title, snippet_text FROM pdf_chunks_metadata")
        rows = cursor.fetchall()
        
        chunks = []
        for r in rows:
            chunks.append({
                "chunk_id": r[0],
                "source_file": r[1],
                "page_number": r[2],
                "section_title": r[3],
                "chunk_text": r[4]
            })
            
        if chunks:
            print(f"Embedding {len(chunks)} chunks for {dataset_name}...")
            stats = embed_chunks(conn, dataset_name, chunks)
            print(f"Result: {stats}\n")
        else:
            print(f"No chunks found in {dataset_name}.db\n")
            
        conn.close()
        
    process_existing_chunks("vistastream")
    process_existing_chunks("neonplay")
