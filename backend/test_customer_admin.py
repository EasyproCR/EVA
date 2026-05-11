"""
Diagnóstico: clientes admin de Alejandra
Ejecutar: python test_customer_admin.py
"""
import sys
import logging
sys.path.append('c:\\laragon\\www\\easycore-eva\\eva\\backend')
logging.basicConfig(level=logging.WARNING)

from app.core.config import get_settings
from app.services.tools.Router.llamaRouter import LlamaRouter
from sqlalchemy import text

settings = get_settings()
router = LlamaRouter(settings)
sql_db = router.db2_sql_db
engine = sql_db._engine

print("\n" + "="*60)
print("DIAGNÓSTICO: Clientes Admin / personal_customers")
print("="*60)

with engine.connect() as conn:

    # 1. Total en personal_customers
    r = conn.execute(text("SELECT COUNT(*) FROM personal_customers"))
    total = r.scalar()
    print(f"\n1. Total registros en personal_customers: {total}")

    # 2. Clientes con asesor identificado
    r = conn.execute(text("""
        SELECT COUNT(*)
        FROM personal_customers pc
        JOIN users u ON pc.user_id = u.id
    """))
    total_linked = r.scalar()
    print(f"2. Con asesor (user_id válido):            {total_linked}")

    # 3. Roles de los asesores que tienen clientes
    print("\n3. Roles de asesores con clientes en personal_customers:")
    r = conn.execute(text("""
        SELECT DISTINCT ro.name as rol, mhr.model_type, COUNT(*) as clientes
        FROM personal_customers pc
        JOIN users u ON pc.user_id = u.id
        JOIN model_has_roles mhr ON mhr.model_id = u.id
        JOIN roles ro ON ro.id = mhr.role_id
        GROUP BY ro.name, mhr.model_type
        ORDER BY clientes DESC
        LIMIT 20
    """))
    for row in r.mappings():
        print(f"   rol='{row['rol']}' | model_type='{row['model_type']}' | clientes={row['clientes']}")

    # 4. Probar el SQL exacto que usa CustomerDataService
    print("\n4. SQL exacto de CustomerDataService (traer todos ADM):")
    roles_in = "'administrator', 'super_admin', 'admin'"
    sql_test = f"""
        SELECT COUNT(*)
        FROM personal_customers pc
        LEFT JOIN users u ON pc.user_id = u.id
        INNER JOIN model_has_roles mhr ON mhr.model_id = u.id
        INNER JOIN roles r ON r.id = mhr.role_id AND r.name IN ({roles_in})
    """
    r = conn.execute(text(sql_test))
    count_adm = r.scalar()
    print(f"   Clientes encontrados con filtro ADM: {count_adm}")

    # 5. Ver qué asesores específicos tienen clientes y sus roles
    print("\n5. Asesores con clientes (nombre + roles):")
    r = conn.execute(text("""
        SELECT u.name as asesor, u.id as user_id,
               GROUP_CONCAT(ro.name ORDER BY ro.name SEPARATOR ', ') as roles,
               COUNT(DISTINCT pc.id) as n_clientes
        FROM personal_customers pc
        JOIN users u ON pc.user_id = u.id
        JOIN model_has_roles mhr ON mhr.model_id = u.id
        JOIN roles ro ON ro.id = mhr.role_id
        GROUP BY u.id, u.name
        ORDER BY n_clientes DESC
        LIMIT 15
    """))
    for row in r.mappings():
        print(f"   {row['asesor']} (id={row['user_id']}) | roles: {row['roles']} | clientes: {row['n_clientes']}")

print("\n" + "="*60)
print("Fin del diagnóstico")
print("="*60)
