import sqlite3

def check_db(db_name):
    conn = sqlite3.connect(f'databases/{db_name}.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM marketing_campaigns WHERE region IS NULL;")
    rows = cursor.fetchall()
    print(f"Table marketing_campaigns in {db_name} where region is NULL:")
    for r in rows:
        print(r)
    conn.close()

check_db('neonplay')
# check_db('vistastream')
