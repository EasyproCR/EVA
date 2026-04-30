import sys
from difflib import SequenceMatcher

EMPLOYEES_KEYWORDS = {
    'expediente', 'expedientes', 'empleado', 'empleados', 'perfil', 'perfiles',
    'contrato', 'contratos', 'puesto', 'puestos', 'salario', 'datos empleado',
    'información empleado', 'ficha empleado', 'staff', 'personal',
    'asesor', 'asesores', 'agente', 'agentes', 'certificado', 'certificados'
}

LEAVES_KEYWORDS = {
    'vacacion', 'vacaciones', 'permiso', 'permisos', 'licencia', 'licencias',
    'días libres', 'ausencia', 'incapacidad', 'baja', 'descanso', 'leave',
    'solicitud de vacaciones', 'solicitud de permiso'
}

LOANS_KEYWORDS = {
    'crédito', 'credito', 'préstamo', 'prestamo', 'adelanto', 'loan', 'credit',
    'credid', 'credid', 'credids', 'creditt', 'creditoo', 'credito', 'creditos',
    'solicitud de crédito', 'solicitud de préstamo', 'solicitud de adelanto',
    'estudio de crédito', 'estudio credito', 'estudio de credid', 'estudio credid',
    'financiamiento', 'financiamiento', 'financiar', 'financiacion',
    'solicitud', 'solicitudes', 'request',
    'aprobación de crédito', 'aprobacion de credito', 'aprobación credid',
    'revisión de crédito', 'revision de credito', 'revisión credid',
    'análisis de crédito', 'analisis de credito', 'análisis credid',
    'cliente', 'clientes', 'propiedad', 'inmueble', 'vivienda', 'casa',
    'cred', 'cred.', 'créditos', 'creditos', 'credito'
}

POLICIES_KEYWORDS = {
    'pauta', 'pautas', 'política', 'politica', 'políticas', 'guideline',
    'código conducta', 'codigo conducta', 'procedimiento', 'procedimientos',
    'política interna', 'norma', 'normas', 'reglamento', 'reglas'
}

REMINDERS_KEYWORDS = {
    'recordatorio', 'recordatorios', 'tatiana', 'tarea', 'tareas', 'pendiente',
    'debido', 'vencimiento', 'administrador', 'reminder', 'alerta', 'alertas'
}

BIRTHDAYS_KEYWORDS = {
    'cumpleaño', 'cumpleaños', 'nacimiento', 'nacimientos', 'aniversario', 'aniversarios',
    'birthday', 'birthdays', 'fecha nacimiento', 'día nacimiento'
}

def _classify_query(query: str):
    query_lower = query.lower()
    words = query_lower.split()
    categories = {
        "EMPLOYEES": EMPLOYEES_KEYWORDS,
        "LEAVES": LEAVES_KEYWORDS,
        "LOANS": LOANS_KEYWORDS,
        "POLICIES": POLICIES_KEYWORDS,
        "REMINDERS": REMINDERS_KEYWORDS,
        "BIRTHDAYS": BIRTHDAYS_KEYWORDS,
    }
    best_match = None
    best_score = 0.0
    matched_word = None
    matched_keyword = None

    for category, keywords in categories.items():
        for word in words:
            for keyword in keywords:
                if keyword in word or word in keyword:
                    print(f"  Coincidencia exacta: '{word}' = '{keyword}' -> {category}")
                    return category

                similarity = SequenceMatcher(None, word, keyword).ratio()
                if similarity >= 0.40 and similarity > best_score:
                    best_score = similarity
                    best_match = category
                    matched_word = word
                    matched_keyword = keyword

    if best_match:
        print(f"  Coincidencia fuzzy ({best_score*100:.0f}%): '{matched_word}' = '{matched_keyword}' -> {best_match}")
    return best_match

print("Testing: eva puedes decirme si hay credid pendientes")
print(_classify_query("eva puedes decirme si hay credid pendientes"))
