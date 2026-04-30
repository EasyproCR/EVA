import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="easycore"
    )
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [r[0] for r in cursor.fetchall()]
    print("TABLES:", tables)
    
    target_tables = [t for t in tables if 'client' in t.lower() or 'customer' in t.lower() or 'lead' in t.lower()]
    print("TARGET TABLES:", target_tables)
    
    for t in target_tables:
        print(f"\n--- Columns for {t} ---")
        cursor.execute(f"SHOW COLUMNS FROM {t}")
        for c in cursor.fetchall():
            print(c[0], c[1])
            
except Exception as e:
    print("Error:", e)
