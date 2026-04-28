import sys
import logging
sys.path.append('c:\\laragon\\www\\easycore-eva\\eva\\backend')
logging.basicConfig(level=logging.DEBUG)

from app.core.config import get_settings
from app.services.tools.Router.llamaRouter import LlamaRouter
from app.services.tools.Router.General.rrhh_data_service import RrhhDataService

settings = get_settings()
router = LlamaRouter(settings)

# get the sql db
sql_db = router.db2_sql_db

service = RrhhDataService(sql_database=sql_db)

# Run process query
res = service.process_query("cuantos creditos credid hay pendientes", ["super_admin"])
print("RESULT:")
print(res)
