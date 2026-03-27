from __future__ import annotations

from typing import Iterable


# Tablas base que suelen ser seguras para cualquier rol autenticado.
COMMON_TABLES: set[str] = {
    "countries",
    "states",
    "cities",
    "segments",
    "departaments",
}


# Mapa canonical role -> tablas permitidas.
ROLE_TABLE_ACCESS: dict[str, set[str]] = {
    "super_admin": {"*"},
    "rrhh": {
        "users",
        "employees",
        "departaments",
        "employee_checklists",
        "leave_requests",
        "loan_requests",
        "policy_guidelines",
        "administrative_reminders",
        "documents",
        "acces_requests",
        "countries",
        "states",
        "cities",
    },
    "soporte": {
        "offers",
        "acces_requests",
        "leave_requests",
        "collaboration_requests",
        "ad_requests",
        "customer_reports",
        "notifications",
        "users",
        "personal_customers",
        "organizations",
        "organization_contacts",
        "credit_study_requests",
        "countries",
        "states",
        "cities",
    },
    "ventas": {
        "financial_controls",
        "financial_movements",
        "expense_controls",
        "expense_payments",
        "billing_controls",
        "offers",
        "credit_study_requests",
        "users",
        "organizations",
        "personal_customers",
    },
    "servicio_al_cliente": {
        "campaigns",
        "campaign_socials",
        "ad_requests",
        "projects",
        "segments",
        "personal_customers",
        "organizations",
    },
    "gerente": {
        "operations",
        "projects",
        "property_assignments",
        "third_party_properties",
        "offers",
        "documents",
        "calendars",
        "table_user_calendar",
        "users",
    },
}


# Alias comunes de nombres de rol en EasyCore.
ROLE_ALIASES: dict[str, str] = {
    "super_admin": "super_admin",
    "rrhh": "rrhh",
    "soporte": "soporte",
    "ventas": "ventas",
    "servicio_al_cliente": "servicio_al_cliente",
    "gerente": "gerente",
}


def normalize_roles(raw_roles: Iterable[str] | None) -> set[str]:
    normalized: set[str] = set()

    if not raw_roles:
        return normalized

    for raw in raw_roles:
        role = str(raw or "").strip().lower()
        if not role:
            continue

        canonical = ROLE_ALIASES.get(role)
        if canonical:
            normalized.add(canonical)
            continue

        # Match por contenido para nombres de rol compuestos.
        if "super_admin" in role:
            normalized.add("super_admin")
        elif "rrhh" in role or "recursos" in role or "human" in role:
            normalized.add("rrhh")
        elif "soporte" in role or "support" in role:
            normalized.add("soporte")
        elif "finan" in role:
            normalized.add("ventas")
        elif "market" in role or "mercadeo" in role:
            normalized.add("servicio_al_cliente")
        elif "oper" in role:
            normalized.add("gerente")

    return normalized


def build_role_scoped_catalog(
    base_catalog: dict[str, str],
    user_roles: Iterable[str] | None,
) -> dict[str, str]:
    roles = normalize_roles(user_roles)

    # Administrador: acceso completo al catalogo (excepto migraciones por seguridad).
    if "administrator" in roles:
        return {
            table: ctx
            for table, ctx in base_catalog.items()
            if table != "migrations"
        }

    allowed_tables = set(COMMON_TABLES)

    for role in roles:
        for table in ROLE_TABLE_ACCESS.get(role, set()):
            if table == "*":
                return {
                    t: c
                    for t, c in base_catalog.items()
                    if t != "migrations"
                }
            allowed_tables.add(table)

    # Sin rol reconocido: solo tablas comunes.
    return {
        table: ctx
        for table, ctx in base_catalog.items()
        if table in allowed_tables and table != "migrations"
    }
