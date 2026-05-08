import sqlite3
import os

def run_query(conn, query, params=()):
    cursor = conn.cursor()
    cursor.execute(query, params)
    return cursor.fetchall()

def verify_db(db_path, env_name, report_file):
    if not os.path.exists(db_path):
        print(f"ERROR: {db_path} not found.")
        return
        
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    tables = ["movies", "viewers", "watch_activity", "reviews", "marketing_campaigns", "regional_performance"]
    
    header = f"=== DATABASE VERIFICATION: {env_name} ===\n"
    report_file.write(header + "\n")
    print(header)
    
    # 2. Verify row counts per table
    for t in tables:
        count = run_query(conn, f"SELECT COUNT(*) FROM {t}")[0][0]
        line = f"{t}: {count} rows"
        print(line)
        report_file.write(line + "\n")
        
    report_file.write("\n")
    print()
    
    # Metrics from ingestion_logs
    rejected = run_query(conn, "SELECT COUNT(*) FROM ingestion_logs WHERE action_taken = 'rejected'")[0][0]
    warnings = run_query(conn, "SELECT COUNT(*) FROM ingestion_logs WHERE log_level = 'WARNING'")[0][0]
    normalizations = run_query(conn, "SELECT COUNT(*) FROM ingestion_logs WHERE action_taken = 'normalized'")[0][0]
    
    metrics = f"Rejected Rows: {rejected}\nWarnings: {warnings}\nNormalizations: {normalizations}\n"
    print(metrics)
    report_file.write(metrics + "\n")
    
    # 4. Query ingestion_logs and summarize
    report_file.write("--- Most Common Warnings ---\n")
    warnings_list = run_query(conn, "SELECT message, COUNT(*) as c FROM ingestion_logs WHERE log_level = 'WARNING' GROUP BY message ORDER BY c DESC LIMIT 5")
    for w in warnings_list:
        report_file.write(f" - {w[1]}x: {w[0]}\n")
        
    report_file.write("\n--- Most Common Errors ---\n")
    errors_list = run_query(conn, "SELECT message, COUNT(*) as c FROM ingestion_logs WHERE log_level = 'ERROR' GROUP BY message ORDER BY c DESC LIMIT 5")
    for e in errors_list:
        report_file.write(f" - {e[1]}x: {e[0]}\n")
        
    report_file.write("\n--- Normalization Frequency ---\n")
    norm_list = run_query(conn, "SELECT message, COUNT(*) as c FROM ingestion_logs WHERE action_taken = 'normalized' GROUP BY message ORDER BY c DESC LIMIT 5")
    for n in norm_list:
        report_file.write(f" - {n[1]}x: {n[0]}\n")
        
    report_file.write("\n--- QA Validation Checks ---\n")
    
    # 5. Verify Startup Normalization Worked
    bad_regions = run_query(conn, "SELECT COUNT(*) FROM viewers WHERE region IN ('Apac', 'Asia Pacific', 'na', 'eu')")
    bad_genres = run_query(conn, "SELECT COUNT(*) FROM movies WHERE genre IN ('SciFi', 'science fiction', 'thriller', 'DRAMA')")
    report_file.write(f"Unnormalized regions found (should be 0): {bad_regions[0][0]}\n")
    report_file.write(f"Unnormalized genres found (should be 0): {bad_genres[0][0]}\n")
    
    # 6. Verify Foreign Key Integrity
    orphan_activities_v = run_query(conn, "SELECT COUNT(*) FROM watch_activity WHERE viewer_id NOT IN (SELECT viewer_id FROM viewers)")
    orphan_activities_m = run_query(conn, "SELECT COUNT(*) FROM watch_activity WHERE movie_id NOT IN (SELECT movie_id FROM movies)")
    report_file.write(f"Orphan watch activities mapped to missing viewers (should be 0): {orphan_activities_v[0][0]}\n")
    report_file.write(f"Orphan watch activities mapped to missing movies (should be 0): {orphan_activities_m[0][0]}\n")
    
    # 7. Verify Startup Invalid Rows Handled
    invalid_comp = run_query(conn, "SELECT COUNT(*) FROM watch_activity WHERE completion_rate < 0 OR completion_rate > 100")
    report_file.write(f"Invalid completion rates remaining (should be 0): {invalid_comp[0][0]}\n")
    
    dup_activities = run_query(conn, "SELECT activity_id, COUNT(*) FROM watch_activity GROUP BY activity_id HAVING COUNT(*) > 1")
    report_file.write(f"Duplicate activity IDs found (should be 0): {len(dup_activities)}\n")

    # 9. Add Sample Diagnostic Queries
    report_file.write("\n--- Sample Diagnostic Queries for Analysis ---\n")
    report_file.write("1. Count rows by region:\n")
    report_file.write("   SELECT region, COUNT(*) FROM viewers GROUP BY region;\n\n")
    
    report_file.write("2. Avg completion by genre:\n")
    report_file.write("   SELECT m.genre, AVG(w.completion_rate) FROM watch_activity w \n")
    report_file.write("   JOIN movies m ON w.movie_id = m.movie_id GROUP BY m.genre;\n\n")
    
    report_file.write("3. Duplicate detection check:\n")
    report_file.write("   SELECT activity_id, COUNT(*) FROM watch_activity GROUP BY activity_id HAVING COUNT(*) > 1;\n")
    
    report_file.write("\n" + "="*50 + "\n\n")
    conn.close()

def generate_report():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(base_dir, "verification_report.txt")
    
    with open(report_path, "w", encoding="utf-8") as f:
        verify_db(os.path.join(base_dir, "databases", "vistastream.db"), "VistaStream Global (Enterprise)", f)
        verify_db(os.path.join(base_dir, "databases", "neonplay.db"), "NeonPlay Media (Startup)", f)
        
    print(f"\nVerification complete. Detailed audit report generated at: {report_path}")

if __name__ == "__main__":
    generate_report()
