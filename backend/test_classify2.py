import sys
sys.path.append('c:\\laragon\\www\\easycore-eva\\eva\\backend')
from app.services.tools.Router.General.rrhh_data_service import RrhhDataService
service = RrhhDataService()
print("CLASSIFY 1:", service._classify_query("eva puedes decirme si hay credid pendientes"))
print("CLASSIFY 2:", service._classify_query("hay solicitudes de crédito pendientes?"))
