import sys
sys.path.append('c:\\laragon\\www\\easycore-eva\\eva\\backend')
from app.services.tools.Router.General.rrhh_data_service import RrhhDataService
from llama_index.core import SQLDatabase
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))
db = SQLDatabase(engine)
service = RrhhDataService(db)

sql = "SELECT id, name, email FROM users WHERE email = 'rrhh@g-easypro.com'"
print(service._execute_query(sql))

sql_roles = "SELECT r.name FROM roles r JOIN model_has_roles mhr ON r.id = mhr.role_id JOIN users u ON u.id = mhr.model_id WHERE u.email = 'rrhh@g-easypro.com'"
print(service._execute_query(sql_roles))
