"""Diagnostico de clientes ADM - ejecutar: python test_customers.py"""
from sqlalchemy import create_engine, text

# Laragon usa puerto 3306 o 3307 dependiendo de la version
for port in [3306, 3307]:
    try:
        engine = create_engine(f'mysql+pymysql://root:@localhost:{port}/easycore', connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"Conectado en puerto {port}")
        break
    except Exception as e:
        print(f"Puerto {port} fallo: {e}")
        engine = None

if not engine:
    print("No se pudo conectar a MySQL")
    exit(1)

with engine.connect() as conn:

    print("\n=== TOTAL REGISTROS personal_customers ===")
    r = conn.execute(text("SELECT COUNT(*) FROM personal_customers"))
    print("Total:", r.scalar())

    print("\n=== PRIMEROS 5 CLIENTES ===")
    r = conn.execute(text("SELECT id, full_name, user_id, customer_need, address FROM personal_customers LIMIT 5"))
    for row in r.mappings():
        print(" ", dict(row))

    print("\n=== VALORES DISTINTOS DE model_type EN model_has_roles ===")
    r = conn.execute(text("SELECT DISTINCT model_type FROM model_has_roles LIMIT 10"))
    for row in r:
        print("  model_type =", repr(row[0]))

    print("\n=== ROLES DISPONIBLES ===")
    r = conn.execute(text("SELECT id, name FROM roles ORDER BY id"))
    for row in r.mappings():
        print(f"  id={row['id']} name={row['name']}")

    print("\n=== JOIN ACTUAL (con model_type LIKE '%User') ===")
    r = conn.execute(text("""
        SELECT COUNT(*) FROM personal_customers pc
        LEFT JOIN users u ON pc.user_id = u.id
        INNER JOIN model_has_roles mhr ON mhr.model_id = u.id AND mhr.model_type LIKE '%User'
        INNER JOIN roles ro ON ro.id = mhr.role_id AND ro.name IN ('administrator','super_admin','admin')
    """))
    print("Resultado:", r.scalar())

    print("\n=== SIN FILTRO model_type ===")
    r = conn.execute(text("""
        SELECT COUNT(*) FROM personal_customers pc
        LEFT JOIN users u ON pc.user_id = u.id
        INNER JOIN model_has_roles mhr ON mhr.model_id = u.id
        INNER JOIN roles ro ON ro.id = mhr.role_id AND ro.name IN ('administrator','super_admin','admin')
    """))
    print("Resultado:", r.scalar())

    print("\n=== ALEJANDRA EN BD ===")
    r = conn.execute(text("""
        SELECT u.id, u.name, u.email, ro.name as rol, mhr.model_type
        FROM users u
        LEFT JOIN model_has_roles mhr ON mhr.model_id = u.id
        LEFT JOIN roles ro ON ro.id = mhr.role_id
        WHERE u.name LIKE '%Alejandra%' OR u.email LIKE '%alejandra%'
        LIMIT 5
    """))
    for row in r.mappings():
        print(" ", dict(row))

    print("\n=== CLIENTES + ROL DE SU ASESOR ===")
    r = conn.execute(text("""
        SELECT pc.full_name, u.name as asesor, ro.name as rol_asesor, mhr.model_type
        FROM personal_customers pc
        LEFT JOIN users u ON pc.user_id = u.id
        LEFT JOIN model_has_roles mhr ON mhr.model_id = u.id
        LEFT JOIN roles ro ON ro.id = mhr.role_id
        LIMIT 10
    """))
    for row in r.mappings():
        print(" ", dict(row))
