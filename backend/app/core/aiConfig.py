from functools import lru_cache
from guardrails import Guard
from guardrails.hub import CorrectLanguage
from app.services.Guard.guardtrails import build_Select_Guard

@lru_cache(maxsize=1)
def build_guard() -> Guard:
    guard = Guard().use(
        CorrectLanguage(expected_language_iso="es", threshold=0.75)
    ).use(
        build_Select_Guard()
    )
    return guard


