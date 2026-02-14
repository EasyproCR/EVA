import re

PROVINCIAS = [
    "san jose", "alajuela", "heredia", "cartago",
    "guanacaste", "puntarenas", "limon"
]

STOPWORDS = {
    # verbos/acciones comunes
    "buscame", "buscar", "busca", "busquen", "busques", "busco",
    "necesito", "ocupo", "quiero", "quisiera", "dame", "ver",
    "mostrame", "muéstrame", "mostrar", "traeme", "traer",
    "ayuda", "ayudame", "info", "informacion", "información",
    "especificamente", "específicamente", "exactamente", "porfavor", "por_favor",

    # artículos/preposiciones/conectores
    "en", "de", "del", "la", "el", "los", "las", "un", "una",
    "por", "para", "que", "con", "sin", "y", "o", "es", "son",
    "tiene", "tienen", "mas", "más", "menos", "muy", "poco", "mucho",
    "bastante", "cerca", "lejos",

    # saludos / fillers
    "hola", "buenas", "buenos", "dias", "días", "tardes", "noches",

    # tipos genéricos (depende si quieres que cuenten como filtro o ruido)
    "propiedad", "propiedades", "casa", "casas", "lote", "lotes", "terreno", "terrenos",

    # adjetivos poco informativos (opcional)
    "barato", "caro", "económico", "economico", "lujoso", "pequeño", "pequeno", "grande",

    # frases que tenías con mayúscula (mejor siempre minúsculas)
    "hay", "esta", "está", "estan", "están", "situada", "ubicada", "localizada",
}


def extraer_filtros(texto: str):
    texto = texto.lower()

    filtros = {}

    # provincia
    for p in PROVINCIAS:
        if re.search(rf"\b{re.escape(p)}\b", texto):
            filtros["provincia"] = p.replace("é","e").replace("ó","o").title()

    match = re.search(
    r"(?:precio|hasta|maximo|máximo|menos de)\s*[:]?[\s]*"
    r"(\d{1,3}(?:[.,]\d{3})*|\d+)\s*(k|mil|millon|millón|millones)?",
    texto
)
    if match:
        raw = match.group(1).replace(".", "").replace(",", "")
        num = int(raw)
        mult = match.group(2)
        if mult in ("k", "mil"):
            num *= 1000
        elif mult in ("millon", "millón"):
            num *= 1_000_000
        elif mult == "millones":
            num *= 1_000_000
        filtros["precio_max"] = num
    return filtros
