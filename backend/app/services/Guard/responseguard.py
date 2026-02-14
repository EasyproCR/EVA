from guardrails import Guard
from guardrails_grhub_regex_match.main import RegexMatch


def build_spanish_response_guard(guard: Guard) -> Guard:

    guard.use(
        RegexMatch,
        regex=r"^(?!.*\b(sql|query|database|tabla|columna|join|select|from|where)\b).*",
        match_type="fullmatch",
        on_fail="fix_reask"
    )

    return guard
