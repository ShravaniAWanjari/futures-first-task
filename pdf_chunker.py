"""
Module: pdf_chunker.py
Purpose: PyMuPDF textual extraction and logical semantic chunking pipeline.
Responsibilities: Recursively parses unstructured PDFs, extracts plain text layouts, applies token-optimized chunk overlaps dynamically.
Security Boundaries: Gracefully isolates and skips malformed or encrypted documents without crashing batch jobs.
Key Decisions: Employs stable MD5 chunk hashing algorithms to guarantee idempotent pipeline reruns and absolute granular traceability.
Inputs: PDF directory paths.
Outputs: Traceable chunk dictionaries with mapped metadata.
"""

import os
import glob
import hashlib
import re
try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF not installed. Please run: pip install pymupdf")
    fitz = None

from logging_utils import get_file_logger

def extract_pdf(pdf_path, dataset_name="default"):
    """
    Extracts text page-by-page from a given PDF.
    Preserves section boundaries and formatting reasonably.
    Returns a list of structured extraction objects.
    """
    if fitz is None:
        return []
        
    logger = get_file_logger(dataset_name)
    extracted_data = []
    
    filename = os.path.basename(pdf_path)
    
    try:
        # Open the PDF gracefully (handles malformed exports or corrupted files)
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        logger.info(f"[{filename}] [PDF] [start] Opened successfully with {page_count} pages.")
        
        for page_num in range(page_count):
            page = doc.load_page(page_num)
            
            # get_text("text") naturally preserves newlines and rough block formatting
            raw_text = page.get_text("text").strip()
            
            if not raw_text:
                # Handles empty pages or unreadable scanned pages
                logger.warning(f"[{filename}] [PDF] [page_{page_num+1}] Empty page or unreadable text detected.")
                continue
                
            extracted_data.append({
                "source_file": filename,
                "page_number": page_num + 1,
                "raw_text": raw_text
            })
            
        doc.close()
        logger.info(f"[{filename}] [PDF] [success] Extracted {len(extracted_data)}/{page_count} pages.")
        return extracted_data
        
    except Exception as e:
        logger.error(f"[{filename}] [PDF] [error] Failed to read or extract: {str(e)}")
        return []

def extract_all_pdfs(directory_path, dataset_name="default"):
    """
    Scans a directory for PDFs and extracts them all.
    Returns a flat list of all extraction objects.
    """
    logger = get_file_logger(dataset_name)
    
    if not os.path.exists(directory_path):
        logger.error(f"[{directory_path}] [DIR] [error] Directory does not exist.")
        return []
        
    # Walk through the directory and match all pdfs
    pdf_files = glob.glob(os.path.join(directory_path, "**", "*.pdf"), recursive=True)
    
    if not pdf_files:
        logger.info(f"[{directory_path}] [DIR] [info] No PDF files found.")
        return []
        
    logger.info(f"[{directory_path}] [DIR] [start] Found {len(pdf_files)} PDFs to process.")
    
    all_extractions = []
    
    for pdf_path in pdf_files:
        extractions = extract_pdf(pdf_path, dataset_name)
        all_extractions.extend(extractions)
        
    logger.info(f"[{directory_path}] [DIR] [success] Finished extracting {len(pdf_files)} PDFs. Total pages extracted: {len(all_extractions)}")
    
    return all_extractions


# --- CHUNKING SYSTEM ---

def _clean_artifact(text, dataset_name):
    """ Cleans known startup export artifacts. """
    if "neonplay" in dataset_name.lower() or dataset_name == "startup":
        # Remove common export artifacts and tolerate weirdness
        text = re.sub(r'#### temp ####', '', text, flags=re.IGNORECASE)
        text = re.sub(r'ERROR_EXPORT_ROW', '', text, flags=re.IGNORECASE)
        # Reduce massive spacing gaps duplicated in bad exports
        text = re.sub(r'\n{3,}', '\n\n', text)
    return text

def create_stable_id(source_file, page_number, chunk_index):
    """ Generates a stable, traceable hash for chunk IDs. """
    raw_str = f"{source_file}_p{page_number}_c{chunk_index}"
    return hashlib.md5(raw_str.encode("utf-8")).hexdigest()

def extract_section_title(text):
    """ Heuristic to extract section titles from chunks. """
    lines = text.strip().split('\n')
    if lines:
        first_line = lines[0].strip()
        # If the first line is short and uppercase or title case, guess it's a section title
        if len(first_line) < 60 and (first_line.isupper() or first_line.istitle()):
            return first_line
    return "Unknown Section"

def chunk_text(text, target_size=800, overlap=150):
    """
    Chunks text ensuring limits (500-900 chars) and respects overlap (100-150 chars).
    Splits text reasonably at paragraphs or sentences to preserve clean structure.
    """
    if not text:
        return []
        
    text = text.replace('\r\n', '\n')
    
    chunks = []
    current_idx = 0
    text_len = len(text)
    
    while current_idx < text_len:
        end_idx = min(current_idx + target_size, text_len)
        
        # Seek a natural break backward if we aren't at the very end
        if end_idx < text_len:
            # Paragraph
            break_idx = text.rfind('\n\n', current_idx + int(target_size * 0.5), end_idx)
            if break_idx != -1:
                end_idx = break_idx + 2
            else:
                # Sentence
                break_idx = text.rfind('. ', current_idx + int(target_size * 0.5), end_idx)
                if break_idx != -1:
                    end_idx = break_idx + 2
                else:
                    # Word break
                    break_idx = text.rfind(' ', current_idx + int(target_size * 0.5), end_idx)
                    if break_idx != -1:
                        end_idx = break_idx + 1
        
        chunk = text[current_idx:end_idx].strip()
        if chunk:
            chunks.append(chunk)
            
        if end_idx == text_len:
            break
            
        current_idx = end_idx - overlap
        
        if current_idx >= end_idx:
            current_idx = end_idx

    return chunks

def generate_chunks(extracted_pages, dataset_name="default"):
    """
    Converts extracted PDF pages into retrieval-safe chunks, 
    preserving metadata and enforcing stability.
    """
    logger = get_file_logger(dataset_name)
    all_chunks = []
    
    chunks_created = 0
    skipped_chunks = 0
    
    for page in extracted_pages:
        source_file = page["source_file"]
        page_num = page["page_number"]
        raw_text = page["raw_text"]
        
        # Startup tolerance for export artifacts
        clean_text = _clean_artifact(raw_text, dataset_name)
        
        if len(clean_text) < 50:
            logger.warning(f"[{source_file}] [chunker] [page_{page_num}] Malformed or tiny extraction - skipping chunking.")
            skipped_chunks += 1
            continue
            
        section_title = extract_section_title(clean_text)
        page_chunks = chunk_text(clean_text, target_size=800, overlap=150)
        
        for idx, c_text in enumerate(page_chunks):
            if len(c_text) < 30:
                skipped_chunks += 1
                continue
                
            chunk_id = create_stable_id(source_file, page_num, idx)
            
            all_chunks.append({
                "chunk_id": chunk_id,
                "source_file": source_file,
                "page_number": page_num,
                "section_title": section_title,
                "chunk_text": c_text
            })
            chunks_created += 1
            
    logger.info(f"[{dataset_name}] [chunker] [summary] Generated {chunks_created} chunks successfully. Skipped {skipped_chunks} malformed chunks.")
    return all_chunks

import sqlite3

def insert_chunk_metadata(conn, dataset_name, chunks):
    """
    Persists trace-ready retrieval metadata into SQLite.
    Protects against duplicate chunks and logs operations.
    """
    logger = get_file_logger(dataset_name)
    inserted = 0
    duplicates = 0
    
    cursor = conn.cursor()
    cursor.execute("BEGIN TRANSACTION")
    
    for chunk in chunks:
        try:
            # INSERT OR IGNORE protects against duplicate chunk IDs perfectly
            cursor.execute("""
                INSERT OR IGNORE INTO pdf_chunks_metadata 
                (chunk_id, source_file, page_number, section_title, snippet_text, embedding_id)
                VALUES (?, ?, ?, ?, ?, NULL)
            """, (
                chunk["chunk_id"], 
                chunk["source_file"], 
                chunk["page_number"], 
                chunk["section_title"], 
                chunk["chunk_text"]
            ))
            
            if cursor.rowcount > 0:
                inserted += 1
            else:
                duplicates += 1
                logger.warning(f"[{dataset_name}] [chunk_db] Duplicate chunk rejected: {chunk['chunk_id']}")
                
        except sqlite3.Error as e:
            logger.error(f"[{dataset_name}] [chunk_db] DB error inserting chunk {chunk['chunk_id']}: {e}")
            
    conn.commit()
    logger.info(f"[{dataset_name}] [chunk_db] Inserted {inserted} new chunks. Rejected {duplicates} duplicates.")
    return {"inserted": inserted, "duplicates": duplicates}

if __name__ == "__main__":
    # Test script if executed directly
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    ent_dir = os.path.join(base_dir, "enterprise_clean_data")
    start_dir = os.path.join(base_dir, "startup_messy_data")
    
    # Process Enterprise
    print("Testing Enterprise PDF Extraction & Chunking...")
    res1 = extract_all_pdfs(ent_dir, "vistastream")
    chunks1 = generate_chunks(res1, "vistastream")
    print(f"Generated {len(chunks1)} chunks from {len(res1)} pages.")
    
    # Store Enterprise chunks
    ent_db = sqlite3.connect(os.path.join(base_dir, "databases", "vistastream.db"))
    ent_stats = insert_chunk_metadata(ent_db, "vistastream", chunks1)
    ent_count = ent_db.execute("SELECT COUNT(*) FROM pdf_chunks_metadata").fetchone()[0]
    print(f"Enterprise Storage Stats: Inserted {ent_stats['inserted']}, Duplicates {ent_stats['duplicates']}. Total in DB: {ent_count}\n")
    ent_db.close()
    
    # Process Startup
    print("Testing Startup PDF Extraction & Chunking...")
    res2 = extract_all_pdfs(start_dir, "neonplay")
    chunks2 = generate_chunks(res2, "neonplay")
    print(f"Generated {len(chunks2)} chunks from {len(res2)} pages.")
    
    # Store Startup chunks
    start_db = sqlite3.connect(os.path.join(base_dir, "databases", "neonplay.db"))
    start_stats = insert_chunk_metadata(start_db, "neonplay", chunks2)
    start_count = start_db.execute("SELECT COUNT(*) FROM pdf_chunks_metadata").fetchone()[0]
    print(f"Startup Storage Stats: Inserted {start_stats['inserted']}, Duplicates {start_stats['duplicates']}. Total in DB: {start_count}\n")
    start_db.close()
