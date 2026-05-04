"""
Test completo del saludo con recordatorios.
Verifica que el flujo funcione desde BD hasta el mensaje final.

Uso: python test_saludo_recordatorios.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import get_settings

settings = get_settings()

# ─────────────────────────────────────────────────────────────────────────────
# 1. Conexión directa a BD de Easycore
# ─────────────────────────────────────────────────────────────────────────────
from sqlalchemy import create_engine, text

print("\n" + "="*60)
print("TEST: SALUDO CON RECORDATORIOS DE CITAS")
print("="*60)

try:
    engine = create_engine(settings.DB_URI_EASYCORE, pool_pre_ping=True)
    print("✅ Conexión a BD Easycore OK")
except Exception as e:
    print(f"❌ Error conectando a BD: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Listar usuarios disponibles para probar
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- USUARIOS EN EL SISTEMA ---")
with engine.connect() as conn:
    result = conn.execute(text("SELECT id, name, email FROM users LIMIT 10"))
    rows = result.fetchall()
    for r in rows:
        print(f"  ID={r[0]} | {r[1]} | {r[2]}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Buscar usuario 'alejandra' o el primero disponible
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- BUSCANDO USUARIO ALEJANDRA ---")
with engine.connect() as conn:
    result = conn.execute(
        text("SELECT id, name, email FROM users WHERE LOWER(name) LIKE '%alejandra%' LIMIT 3")
    )
    rows = result.fetchall()
    if rows:
        for r in rows:
            print(f"  ✅ Encontrada: ID={r[0]} | {r[1]} | {r[2]}")
        test_user_id = rows[0][0]
    else:
        print("  ⚠️ No se encontró 'alejandra', usando ID=1 para test")
        test_user_id = 1

print(f"\n  → Usando user_id={test_user_id} para el test")

# ─────────────────────────────────────────────────────────────────────────────
# 4. Verificar tabla customer_reminders
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- VERIFICANDO TABLA customer_reminders ---")
with engine.connect() as conn:
    try:
        result = conn.execute(
            text("""
            SELECT cr.id, cr.reminder_type, cr.reminder_date, cr.status,
                   c.full_name as cliente
            FROM customer_reminders cr
            LEFT JOIN customers c ON cr.customer_id = c.id
            WHERE cr.user_id = :uid
            ORDER BY cr.reminder_date ASC
            LIMIT 10
            """),
            {"uid": test_user_id}
        )
        rows = result.fetchall()
        if rows:
            print(f"  ✅ {len(rows)} recordatorio(s) encontrados para user_id={test_user_id}:")
            for r in rows:
                print(f"     [{r[3]}] {r[1]} | Cliente: {r[4]} | Fecha: {r[2]}")
        else:
            print(f"  ⚠️ No hay recordatorios para user_id={test_user_id}")
            # Mostrar todos los user_id con recordatorios
            result2 = conn.execute(text(
                "SELECT user_id, COUNT(*) as total FROM customer_reminders GROUP BY user_id LIMIT 10"
            ))
            all_rows = result2.fetchall()
            if all_rows:
                print("  → user_ids CON recordatorios en BD:")
                for r in all_rows:
                    print(f"     user_id={r[0]} → {r[1]} recordatorio(s)")
            else:
                print("  → La tabla customer_reminders está vacía")
    except Exception as e:
        print(f"  ❌ Error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Simular el get_pending_reminders_for_greeting
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- SIMULANDO get_pending_reminders_for_greeting ---")
from llama_index.core import Settings as LlamaSettings
from llama_index.llms.openai import OpenAI
LlamaSettings.llm = OpenAI(api_key=settings.openai_api_key, model=settings.openai_model)

from llama_index.embeddings.openai.base import OpenAIEmbedding
LlamaSettings.embed_model = OpenAIEmbedding(api_key=settings.openai_api_key)

from app.services.tools.Router.SQLQuery.llamaSQLquery import LlamaSQLQuery
sql_db = LlamaSQLQuery(settings.DB_URI_EASYCORE).get_sql_database()

from app.services.tools.Router.General.customer_reminders_service import CustomerRemindersService
svc = CustomerRemindersService(sql_database=sql_db)
result_dict = svc.get_pending_reminders_for_greeting(test_user_id)
print(f"  count = {result_dict['count']}")
for r in result_dict.get('reminders', []):
    print(f"  {r['emoji']} {r['titulo']} | {r['fecha_vencimiento']} → {r['accion']}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. Simular el get_operations_reminders
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- SIMULANDO get_operations_reminders ---")
from app.services.tools.Router.General.operations_data_service import OperationsDataService
ops_svc = OperationsDataService(sql_database=sql_db)
ops_result = ops_svc.get_pending_reminders_for_greeting(test_user_id)
print(f"  count = {ops_result['count']}")
for r in ops_result.get('reminders', []):
    print(f"  {r['emoji']} {r['titulo']} | {r['fecha_vencimiento']} → {r['accion']}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Simular el mensaje final de saludo
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- MENSAJE FINAL DE SALUDO ---")
saludo_texto = "¡Hola Alejandra! Soy EVA, tu asistente de IA."

total_reminders = result_dict['count'] + ops_result['count']

if result_dict['count'] > 0:
    saludo_texto += f"\n\n📞 **Tienes {result_dict['count']} recordatorio(s) de cliente(s):**\n"
    for r in result_dict['reminders']:
        fecha = r.get('fecha_vencimiento', '')
        saludo_texto += f"\n{r['emoji']} **{r['titulo']}**"
        if fecha and fecha not in ('None', ''):
            saludo_texto += f" - {fecha}"
        saludo_texto += f"\n   _→ {r['accion']}_"

if ops_result['count'] > 0:
    saludo_texto += f"\n\n📅 **Tienes {ops_result['count']} cita(s) pendiente(s):**\n"
    for r in ops_result['reminders']:
        fecha = r.get('fecha_vencimiento', '')
        saludo_texto += f"\n{r['emoji']} **{r['titulo']}**"
        if fecha and fecha not in ('None', ''):
            saludo_texto += f" - {fecha}"
        saludo_texto += f"\n   _→ {r['accion']}_"

if total_reminders == 0:
    saludo_texto += "\n\n✅ No tienes citas ni recordatorios pendientes por ahora."

saludo_texto += "\n\n¿En qué puedo ayudarte hoy?"

print(saludo_texto)
print("\n" + "="*60)
print(f"RESULTADO: {total_reminders} recordatorio(s) total")
print("="*60)
