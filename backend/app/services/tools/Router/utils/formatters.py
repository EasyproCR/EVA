"""
Utilidades compartidas para formateo de datos.
Centraliza funciones comunes usadas en múltiples query engines.
"""

from typing import Any, Dict, List, Union, Optional


def format_price(price: Union[int, float, str, None], default: str = "N/D") -> str:
    """
    Formatea un precio en USD con separadores miles.

    Args:
        price: Precio como número o string
        default: Valor por defecto si no se puede convertir

    Returns:
        String formateado "USD X,XXX.XX" o el valor por defecto
    """
    if price is None or price == "":
        return default

    try:
        price_float = float(price)
        return f"USD {price_float:,.0f}"
    except (ValueError, TypeError):
        return default


def format_location(data: Dict[str, Any]) -> str:
    """
    Formatea ubicación como "Provincia, Cantón, Distrito".
    Maneja valores faltantes elegantemente.

    Args:
        data: Diccionario con claves 'provincia', 'canton', 'distrito'

    Returns:
        String formateado de ubicación
    """
    provincia = data.get('provincia', 'Desconocida')
    canton = data.get('canton', '')
    distrito = data.get('distrito', '')

    parts = [str(p) for p in [provincia, canton, distrito] if p and str(p).strip()]
    return ", ".join(parts) if parts else "Ubicación desconocida"


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Convierte un valor a float de forma segura.

    Args:
        value: Valor a convertir
        default: Valor por defecto si falla la conversión

    Returns:
        float: El valor convertido o el default
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def group_by_key(items: List[Dict], key: str) -> Dict[str, List[Dict]]:
    """
    Agrupa una lista de diccionarios por un campo específico.

    Args:
        items: Lista de diccionarios
        key: Campo por el cual agrupar

    Returns:
        Diccionario donde las claves son valores del campo y los valores son listas de items
    """
    result = {}
    for item in items:
        group_key = item.get(key) or "Desconocido"
        if group_key not in result:
            result[group_key] = []
        result[group_key].append(item)
    return result


def count_by_key(items: List[Dict], key: str, filter_empty: bool = False) -> Dict[str, int]:
    """
    Cuenta ocurrencias de cada valor en un campo.

    Args:
        items: Lista de diccionarios
        key: Campo a contar
        filter_empty: Si True, no cuenta valores None o vacíos

    Returns:
        Diccionario con conteos por valor
    """
    result = {}
    for item in items:
        value = item.get(key)

        if filter_empty and (value is None or value == ""):
            continue

        value_str = str(value) if value is not None else "Desconocido"
        result[value_str] = result.get(value_str, 0) + 1

    return result
