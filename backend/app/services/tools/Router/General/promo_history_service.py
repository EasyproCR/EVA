"""
Promo History Service - Rastrea qué estrategias se generaron por semana ISO
No requiere tabla en BD: usa rotación matemática por número de semana.
Compatible con múltiples propiedades y múltiples usuarios.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Directorio donde se guarda el historial (relativo a este archivo)
_HISTORY_DIR = os.path.join(os.path.dirname(__file__), "_promo_history")


def _ensure_dir():
    os.makedirs(_HISTORY_DIR, exist_ok=True)


def _history_file(property_id: int) -> str:
    return os.path.join(_HISTORY_DIR, f"promo_{property_id}.json")


def _current_week() -> Tuple[int, int]:
    """Retorna (año, semana_iso) actual."""
    now = datetime.now()
    iso = now.isocalendar()
    return iso[0], iso[1]  # (year, week)


# ─────────────────────────────────────────────────────────────────────────────
# Temas rotativos — 8 bloques para cubrir dos meses sin repetir
# ─────────────────────────────────────────────────────────────────────────────
WEEKLY_THEMES = [
    {
        "semana_relativa": 1,
        "enfoque": "Primera impresión poderosa",
        "descripcion": "Presentación de la propiedad: tour visual completo, fachada e interiores",
        "formatos": [
            "Reel de 30 seg: tour rápido con música dinámica",
            "Carrusel en Instagram: 5-7 fotos con descripción de cada espacio",
            "Story de 'Antes de entrar': teaser de la fachada",
        ],
        "angulo": "aspiracional",
        "cta": "¿Te imaginas vivir aquí? 💫 Escríbenos para coordinar una cita",
    },
    {
        "semana_relativa": 2,
        "enfoque": "Ubicación como estrella",
        "descripcion": "Mostrar el vecindario, accesos, servicios cercanos y puntos de referencia",
        "formatos": [
            "Reel con mapa animado mostrando distancias a supermercados, colegios, hospitales",
            "Post de texto: '¿Qué tan bien ubicada está esta propiedad?' + puntos clave",
            "Story en formato 'A X minutos de...': slide por slide con cada servicio cercano",
        ],
        "angulo": "informativo / práctico",
        "cta": "Vive cerca de todo lo que necesitas 🗺️ Consulta disponibilidad",
    },
    {
        "semana_relativa": 3,
        "enfoque": "Números que convencen",
        "descripcion": "Mostrar el valor financiero: precio, cotización, comparación con el mercado",
        "formatos": [
            "Post tipo infografía: precio vs. mercado en la zona",
            "Reel de 'Por menos de X puedes tener esto': tour rápido enfocando el precio",
            "Story con calculadora: 'Tu cuota mensual aproximada sería...'",
        ],
        "angulo": "financiero / oportunidad",
        "cta": "Una oportunidad real 💰 Solicita tu cotización personalizada hoy",
    },
    {
        "semana_relativa": 4,
        "enfoque": "Estilo de vida que ofrece",
        "descripcion": "Mostrar el lifestyle que acompaña a la propiedad según su entorno",
        "formatos": [
            "Reel al amanecer o atardecer en el exterior de la propiedad",
            "Post: 'Así sería tu domingo en esta propiedad' (descripción aspiracional)",
            "Story con pregunta: '¿Cuál sería tu rincón favorito?' + opciones",
        ],
        "angulo": "emocional / lifestyle",
        "cta": "Tu nuevo estilo de vida te está esperando 🌅 ¡Contáctanos!",
    },
    {
        "semana_relativa": 5,
        "enfoque": "Detalles que enamoran",
        "descripcion": "Primeros planos de los detalles únicos: acabados, ventanas, espacios especiales",
        "formatos": [
            "Reel de close-ups con música suave: acabados, pisos, ventanas, cocina",
            "Carrusel: cada slide resalta un detalle especial con una línea de texto",
            "Story tipo 'encuentra el detalle' interactivo",
        ],
        "angulo": "detalle / calidad",
        "cta": "Los detalles marcan la diferencia ✨ Agendá tu visita",
    },
    {
        "semana_relativa": 6,
        "enfoque": "Comparación con el mercado",
        "descripcion": "Posicionar la propiedad frente a otras opciones en la zona",
        "formatos": [
            "Post: '¿Por qué elegir esta propiedad vs. otras en [zona]?' con checklist",
            "Reel estilo 'Lo que otros no te dan': características diferenciales",
            "Story encuesta: '¿Qué valoras más en una propiedad?'",
        ],
        "angulo": "comparativo / educativo",
        "cta": "Compará y decidí 🏆 Esta propiedad tiene lo que otras no",
    },
    {
        "semana_relativa": 7,
        "enfoque": "Testimonio o historia",
        "descripcion": "Humanizar la propiedad: historia, potencial, sueño realizado",
        "formatos": [
            "Post de storytelling: 'Esta propiedad tiene historia...' (narrativa)",
            "Reel tipo 'El antes de tu historia' — imaginando la vida en la propiedad",
            "Story formato Q&A: responder 3 preguntas frecuentes sobre esta propiedad",
        ],
        "angulo": "emocional / confianza",
        "cta": "Escribí tu propia historia aquí 📖 Hablemos",
    },
    {
        "semana_relativa": 8,
        "enfoque": "Urgencia y cierre",
        "descripcion": "Crear sentido de urgencia: oportunidad limitada, momento ideal para comprar",
        "formatos": [
            "Post de urgencia: 'Esta propiedad no durará mucho' con datos reales",
            "Reel fast-paced con texto de urgencia: '¿Cuánto tiempo falta?'",
            "Story con countdown o 'última semana para aprovechar estas condiciones'",
        ],
        "angulo": "urgencia / cierre",
        "cta": "El momento es AHORA ⏰ No dejés pasar esta oportunidad",
    },
]


def get_week_theme(property_id: int) -> Dict:
    """
    Retorna el tema de la semana actual para esta propiedad.
    Usa el número de semana ISO para rotar entre los 8 temas,
    con un offset por property_id para que distintas propiedades varíen.

    Args:
        property_id: ID de la propiedad

    Returns:
        Dict con el tema de esta semana
    """
    _ensure_dir()
    year, week = _current_week()

    # Offset por propiedad para que diferentes propiedades no tengan el mismo tema
    theme_index = (week + property_id) % len(WEEKLY_THEMES)
    theme = WEEKLY_THEMES[theme_index].copy()
    theme["year"] = year
    theme["week"] = week
    theme["theme_index"] = theme_index

    logger.info(
        f"📅 Tema semana {week}/{year} para propiedad {property_id}: "
        f"'{theme['enfoque']}' (índice {theme_index})"
    )
    return theme


def get_next_week_theme(property_id: int) -> Dict:
    """Retorna el tema de la PRÓXIMA semana para previsión."""
    year, week = _current_week()
    next_week = week + 1
    next_year = year
    if next_week > 52:
        next_week = 1
        next_year = year + 1

    theme_index = (next_week + property_id) % len(WEEKLY_THEMES)
    theme = WEEKLY_THEMES[theme_index].copy()
    theme["year"] = next_year
    theme["week"] = next_week
    theme["theme_index"] = theme_index
    return theme


def log_strategy_generated(property_id: int, user_id: int = None):
    """
    Registra que se generó una estrategia esta semana para esta propiedad.
    Persiste en archivo JSON para referencia.
    """
    _ensure_dir()
    year, week = _current_week()
    history_file = _history_file(property_id)

    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    entry = {
        "year": year,
        "week": week,
        "generated_at": datetime.now().isoformat(),
        "user_id": user_id,
        "theme": get_week_theme(property_id)["enfoque"],
    }

    # Evitar duplicados de la misma semana
    history = [h for h in history if not (h["year"] == year and h["week"] == week)]
    history.append(entry)

    # Mantener solo últimas 12 semanas
    history = sorted(history, key=lambda x: (x["year"], x["week"]))[-12:]

    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Historial guardado para propiedad {property_id} semana {week}/{year}")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo guardar historial: {e}")


def was_generated_this_week(property_id: int) -> bool:
    """Verifica si ya se generó una estrategia esta semana para esta propiedad."""
    _ensure_dir()
    year, week = _current_week()
    history_file = _history_file(property_id)

    if not os.path.exists(history_file):
        return False

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
        return any(h["year"] == year and h["week"] == week for h in history)
    except Exception:
        return False


def get_all_active_property_ids() -> List[int]:
    """
    Retorna todos los IDs de propiedades que tienen historial de estrategia.
    Usado para las notificaciones semanales.
    """
    _ensure_dir()
    ids = []
    for fname in os.listdir(_HISTORY_DIR):
        if fname.startswith("promo_") and fname.endswith(".json"):
            try:
                pid = int(fname.replace("promo_", "").replace(".json", ""))
                ids.append(pid)
            except ValueError:
                pass
    return ids


def get_weekly_notification_message(property_id: int, property_name: str = None) -> Optional[str]:
    """
    Genera el mensaje de notificación semanal para una propiedad.
    Retorna None si ya se notificó esta semana.

    Args:
        property_id: ID de la propiedad
        property_name: Nombre de la propiedad (para personalizar el mensaje)

    Returns:
        Mensaje de notificación o None
    """
    if was_generated_this_week(property_id):
        return None

    theme = get_week_theme(property_id)
    year, week = _current_week()
    prop_label = f"**{property_name}**" if property_name else f"propiedad ID {property_id}"

    msg = (
        f"📅 **Sugerencia de contenido — Semana {week}**\n\n"
        f"Para la {prop_label}, esta semana te recomiendo enfocarte en:\n\n"
        f"🎯 **{theme['enfoque']}**\n"
        f"{theme['descripcion']}\n\n"
        f"**Formatos sugeridos:**\n"
    )
    for fmt in theme["formatos"]:
        msg += f"  • {fmt}\n"

    msg += (
        f"\n**Ángulo de comunicación:** {theme['angulo']}\n"
        f"**CTA sugerido:** {theme['cta']}\n\n"
        f"_💡 La próxima semana el enfoque será: **{get_next_week_theme(property_id)['enfoque']}**_"
    )
    return msg
