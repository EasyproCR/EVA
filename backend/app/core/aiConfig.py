from functools import lru_cache

from guardrails import Guard
from app.services.Guard.guardtrails import build_Select_Guard
from app.services.Guard.responseguard import build_spanish_response_guard


@lru_cache(maxsize=1)
def build_guard():
    guard = Guard()

    build_Select_Guard(guard)
    build_spanish_response_guard(guard)

    return guard