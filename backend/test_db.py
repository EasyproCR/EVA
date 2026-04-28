import sys
sys.path.append('c:\\laragon\\www\\easycore-eva\\eva\\backend')
from app.core.config import get_settings
from sqlalchemy import create_engine, text

settings = get_settings()
engine = create_engine(getattr(settings, 'DB_URI_EASYCORE'))
with engine.connect() as conn:
    print("Statuses:")
    try:
        res = conn.execute(text('SELECT request_status, COUNT(*) FROM credit_study_requests GROUP BY request_status')).fetchall()
        print(res)
    except Exception as e:
        print(e)
    print("Employees credid:")
    try:
        res = conn.execute(text("SELECT count(*) FROM employees WHERE credid IS NOT NULL AND credid != ''")).fetchall()
        print(res)
    except Exception as e:
        print(e)
