import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load from backend folder
load_dotenv('c:\\laragon\\www\\easycore-eva\\eva\\backend\\.env')

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("NO DATABASE URL!")
    sys.exit(1)

engine = create_engine(db_url)
try:
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES"))
        tables = [r[0] for r in result]
        print("TABLES:", tables)
        
        # Look for customer/client tables
        target_tables = [t for t in tables if 'client' in t.lower() or 'customer' in t.lower()]
        print("TARGET TABLES:", target_tables)
        
        for t in target_tables:
            print(f"\n--- Columns for {t} ---")
            cols = conn.execute(text(f"SHOW COLUMNS FROM {t}"))
            for c in cols:
                print(c[0], c[1])
                
except Exception as e:
    print("Error:", e)
