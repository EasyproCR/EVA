TABLE_CATALOG_EASYCORE = {
  # =========================
  # P1 - Core (según PDF)
  # =========================
  "users": (
    "(DB Bienes) Usuarios del sistema: acceso/autenticación y perfil base. "
    "Usar para consultas de cuentas, nombres, correos, ownership de registros. "
    "P1 core; entidad central del sistema."
  ),  # :contentReference[oaicite:1]{index=1}

  "employees": (
    "(DB Bienes) RRHH del personal (detalle del empleado): contratos, puesto, salario, dirección, documentos personales. "
    "Relación 1:1 con users; pertenece a un departamento. P1."
  ),  # :contentReference[oaicite:2]{index=2}

  "personal_customers": (
    "(DB Bienes) Clientes individuales y prospectos (CRM): contacto, preferencias, presupuesto, seguimiento comercial. "
    "Crítico para preguntas tipo '¿Quién es el cliente X?' o '¿Qué busca?'. P1."
  ),  # :contentReference[oaicite:3]{index=3}

  "organizations": (
    "(DB Bienes) Organizaciones/empresas (clientes corporativos y aliados). "
    "Útil para consultas B2B, convenios, relación comercial. P1."
  ),  # :contentReference[oaicite:4]{index=4}

  "offers": (
    "(DB Bienes) Ofertas/negociaciones por propiedades: montos (USD/CRC) y estado (pendiente/aceptada/rechazada). "
    "Conecta clientes (personal_customers) con la propiedad. P1."
  ),  # :contentReference[oaicite:5]{index=5}

  "third_party_properties": (
    "(DB Bienes) Inventario de inmuebles (captación): detalles técnicos, legales y comerciales; venta/alquiler. "
    "Fuente principal de inventario disponible. P1."
  ),  # :contentReference[oaicite:6]{index=6}

  "financial_controls": (
    "(DB Bienes) Cabecera de controles financieros: préstamos/cuentas/facturas adelantadas/financiamientos. "
    "P1 finanzas; se complementa con financial_movements."
  ),  # :contentReference[oaicite:7]{index=7}

  "financial_movements": (
    "(DB Bienes) Movimientos/transacciones: abonos, cargos, flujo de caja detallado asociado a financial_controls. "
    "P1 finanzas."
  ),  # :contentReference[oaicite:8]{index=8}

  # =========================
  # P2 - Operación/Marketing/Solicitudes (según PDF)
  # =========================
  "operations": (
    "(DB Bienes) Base de conocimiento operativa (SOPs): procesos, políticas y pasos estandarizados. "
    "Útil para preguntas '¿Cómo hago X?' (procedimientos internos). P2."
  ),  # :contentReference[oaicite:9]{index=9}

  "campaigns": (
    "(DB Bienes) Campañas de marketing: seguimiento de esfuerzos publicitarios y resultados. P2."
  ),  # :contentReference[oaicite:10]{index=10}

  "projects": (
    "(DB Bienes) Proyectos internos: gestión macro de iniciativas/entregables. P2."
  ),  # :contentReference[oaicite:11]{index=11}

  "expense_controls": (
    "(DB Bienes) Controles de gastos fijos/recurrentes: automatización y registro de gastos. P2."
  ),  # :contentReference[oaicite:12]{index=12}

  "leave_requests": (
    "(DB Bienes) Solicitudes de vacaciones/permisos: gestión de ausencias del personal. P2."
  ),  # :contentReference[oaicite:13]{index=13}

  # =========================
  # Complementos útiles (no descritos explícitamente en PDF)
  # =========================
  "customers": (
    "(DB Bienes) Clientes (genérico): puede ser capa agregada/legado; confirmar si convive con personal_customers/organizations. "
    "Usar para consultas amplias de clientes si aplica."
  ),

  "organization_contacts": (
    "(DB Bienes) Contactos asociados a organizaciones: personas, teléfonos, emails, cargos. "
    "Usar para 'contacto de la empresa X'."
  ),

  "credit_study_requests": (
    "(DB Bienes) Solicitudes de estudio de crédito/financiamiento: estado del trámite, entidad financiera, monto, condiciones. "
    "Útil para venta con financiamiento y asesoría."
  ),

  "customer_reports": (
    "(DB Bienes) Reportes asociados a clientes/prospectos (seguimiento/comercial)."
  ),

  "property_assignments": (
    "(DB Bienes) Asignaciones de propiedades a usuarios/agentes/equipos (ownership/responsables)."
  ),

  "calendars": (
    "(DB Bienes) Calendarios (agenda): eventos, disponibilidad, recordatorios vinculados a usuarios/procesos."
  ),

  "table_user_calendar": (
    "(DB Bienes) Tabla pivote usuario↔calendario (relación many-to-many)."
  ),

  "notifications": (
    "(DB Bienes) Notificaciones del sistema (eventos/alertas a usuarios)."
  ),

  "admin_reminders": (
    "(DB Bienes) Recordatorios administrativos: reglas/plantillas para notificar o dar seguimiento."
  ),

  "admin_reminder_runs": (
    "(DB Bienes) Ejecuciones/historial de recordatorios (runs): cuándo se disparó, estado, resultados."
  ),

  "documents": (
    "(DB Bienes) Documentos (metadata): archivos legales, contratos, fotos, anexos; referencia a storage (S3/Blob/local)."
  ),

  "dms_persistent_objects": (
    "(DB Bienes) Objetos persistentes del DMS (document management): referencias internas, versionado o punteros a blobs."
  ),

  "campaign_socials": (
    "(DB Bienes) Publicaciones/artefactos de campañas en redes sociales: canal, métricas, contenido, scheduling."
  ),

  "collaboration_requests": (
    "(DB Bienes) Solicitudes de colaboración/alianzas: instituciones, convenios, referidos, partners."
  ),

  "acces_requests": (
    "(DB Bienes) Solicitudes de acceso (onboarding/roles/permisos)."
  ),

  "ad_requests": (
    "(DB Bienes) Solicitudes de pauta/anuncios: alta de campañas, presupuestos, aprobaciones."
  ),

  "employee_checklists": (
    "(DB Bienes) Checklists de empleados: onboarding, tareas recurrentes, cumplimiento."
  ),

  "expense_payments": (
    "(DB Bienes) Pagos/ejecuciones de gastos: registros detallados asociados a expense_controls."
  ),

  "billing_controls": (
    "(DB Bienes) Controles de facturación/cobro: ciclos, estados, montos, referencias."
  ),

  "jobs": (
    "(DB Bienes) Jobs/colas (framework): tareas asíncronas, estado, payload resumido."
  ),

  "failed_jobs": (
    "(DB Bienes) Jobs fallidos: error, payload, timestamp; útil para troubleshooting."
  ),

  "filament_comments": (
    "(DB Bienes) Comentarios internos (Filament/admin): notas sobre entidades, auditoría ligera."
  ),

  "sessions": (
    "(DB Bienes) Sesiones de usuario: tokens/estado (depende del stack)."
  ),

  "password_reset_tokens": (
    "(DB Bienes) Tokens de reset de contraseña (seguridad)."
  ),

  "personal_access_tokens": (
    "(DB Bienes) Tokens personales/API (auth tipo Sanctum/Passport)."
  ),

  "permissions": (
    "(DB Bienes) Permisos del sistema (RBAC)."
  ),

  "roles": (
    "(DB Bienes) Roles del sistema (RBAC)."
  ),

  "model_has_roles": (
    "(DB Bienes) Asignación modelo↔roles (RBAC pivot)."
  ),

  "model_has_permissions": (
    "(DB Bienes) Asignación modelo↔permisos (RBAC pivot)."
  ),

  "role_has_permissions": (
    "(DB Bienes) Asignación rol↔permisos (RBAC pivot)."
  ),

  "departaments": (
    "(DB Bienes) Departamentos internos (estructura organizacional). P3 según esquema general."
  ),  # :contentReference[oaicite:14]{index=14}

  "countries": (
    "(DB Bienes) Catálogo de países (geografía)."
  ),

  "states": (
    "(DB Bienes) Catálogo de provincias/estados (geografía)."
  ),

  "cities": (
    "(DB Bienes) Catálogo de ciudades/cantones/distritos (geografía)."
  ),

  "segments": (
    "(DB Bienes) Segmentos de clientes/mercado: inversionista, vivienda, empresa; reglas de segmentación."
  ),

  "migrations": (
    "(DB Bienes) Migraciones del ORM/framework (control de esquema)."
  ),
}
