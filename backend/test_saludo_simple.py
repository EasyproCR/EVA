"""
Test simple de recordatorios - solo BD, sin LlamaIndex.
Levanta Laragon antes de correr este script.

Uso: python test_saludo_simple.py
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import get_settings
from sqlalchemy import create_engine, text

settings = get_settings()

print("="*60)
print("TEST RAPIDO: RECORDATORIOS PARA ALEJANDRA")
print("="*60)

engine = create_engine(settings.DB_URI_EASYCORE, pool_pre_ping=True)

with engine.connect() as conn:

    # 1. Buscar a Alejandra
    print("\n[1] Buscando usuario Alejandra...")
    r = conn.execute(text("SELECT id, name FROM users WHERE LOWER(name) LIKE '%alejandra%' LIMIT 3"))
    users = r.fetchall()
    if users:
        for u in users:
            print(f"    ID={u[0]} | {u[1]}")
        user_id = users[0][0]
    else:
        print("    No encontrado. Listando primeros 5 usuarios:")
        r2 = conn.execute(text("SELECT id, name FROM users LIMIT 5"))
        for u in r2.fetchall():
            print(f"    ID={u[0]} | {u[1]}")
        user_id = input("\n    Ingresa el ID de usuario a probar: ").strip()
        user_id = int(user_id)

    print(f"\n    => Usando user_id = {user_id}")

    # 2. Ver todos los recordatorios del usuario (sin filtrar tipo)
    print(f"\n[2] Todos los recordatorios de user_id={user_id}:")
    r = conn.execute(text("""
        SELECT cr.id, cr.reminder_type, cr.status, cr.reminder_date,
               COALESCE(c.full_name, 'sin cliente') as cliente
        FROM customer_reminders cr
        LEFT JOIN customers c ON cr.customer_id = c.id
        WHERE cr.user_id = :uid
        ORDER BY cr.reminder_date ASC
        LIMIT 20
    """), {"uid": user_id})
    rows = r.fetchall()
    if rows:
        print(f"    {len(rows)} registro(s) encontrados:")
        for row in rows:
            print(f"    ID={row[0]} | tipo={row[1]} | estado={row[2]} | fecha={row[3]} | cliente={row[4]}")
    else:
        print("    Sin recordatorios para este usuario.")
        # Mostrar user_ids que sí tienen
        r2 = conn.execute(text(
            "SELECT user_id, COUNT(*) c FROM customer_reminders GROUP BY user_id ORDER BY c DESC LIMIT 10"
        ))
        print("\n    user_ids CON recordatorios:")
        for row in r2.fetchall():
            print(f"    user_id={row[0]} => {row[1]} registros")

    # 3. Ver tipos de reminder_type disponibles
    print(f"\n[3] Valores de reminder_type en la BD:")
    r = conn.execute(text("SELECT DISTINCT reminder_type FROM customer_reminders LIMIT 20"))
    tipos = [row[0] for row in r.fetchall()]
    print(f"    {tipos}")

    # 4. Ver estados disponibles
    print(f"\n[4] Valores de status en la BD:")
    r = conn.execute(text("SELECT DISTINCT status FROM customer_reminders LIMIT 20"))
    estados = [row[0] for row in r.fetchall()]
    print(f"    {estados}")

    # 5. Simular la query exacta que usa el sistema
    print(f"\n[5] Query del sistema (appointment + pending/in_progress + fecha futura):")
    r = conn.execute(text("""
        SELECT cr.id, cr.reminder_date, cr.status,
               COALESCE(c.full_name, 'sin cliente') as customer_name
        FROM customer_reminders cr
        LEFT JOIN customers c ON cr.customer_id = c.id
        WHERE cr.user_id = :uid
        AND cr.reminder_type = 'appointment'
        AND cr.status IN ('pending', 'in_progress')
        AND cr.reminder_date >= CURDATE()
        ORDER BY cr.reminder_date ASC
        LIMIT 10
    """), {"uid": user_id})
    rows = r.fetchall()
    if rows:
        print(f"    {len(rows)} cita(s) pendiente(s):")
        for row in rows:
            print(f"    {row[3]} | {row[1]} | estado={row[2]}")
    else:
        print("    Sin resultados con esos filtros exactos.")

print("\n" + "="*60)
print("FIN DEL TEST")
print("="*60)
