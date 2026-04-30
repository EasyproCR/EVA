import sys
sys.path.append('c:\\laragon\\www\\easycore-eva\\eva\\backend')
from app.services.tools.Router.General.rrhh_data_service import RrhhDataService
service = RrhhDataService()
print("CLASSIFY:", service._classify_query("puedes decirme si hay solicitudes de credito pendientes"))
print("CLASSIFY 2:", service._classify_query("puedes decirme si hay solicitudes de crédito pendientes"))
