"""
Property Promo Engine - Genera estrategia de promoción para una propiedad por ID.
Alejandra puede pedir: "estrategia para ID 150" y EVA genera el plan completo.
"""

import re
import logging
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional, Dict

from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager
from llama_index.core import Settings

from app.services.tools.Router.General.promo_history_service import (
    get_week_theme,
    get_next_week_theme,
    log_strategy_generated,
    get_weekly_notification_message,
)

logger = logging.getLogger(__name__)


class PropertyPromoEngine(BaseQueryEngine):
    """
    Engine que analiza una propiedad y genera un plan estratégico de promoción
    personalizado: plataformas, ideas de video/contenido, hashtags, audiencia.
    Cada semana genera contenido DIFERENTE al de la semana anterior.

    Trigger: "estrategia para ID 150", "promociona la propiedad 200",
             "plan de marketing ID 432", "cómo promociono el ID 90"
    Acceso: Abierto para todos los usuarios.
    """

    PROMO_KEYWORDS = {
        'estrategia', 'estrategia de', 'promoci', 'promoción', 'promocion',
        'marketing', 'publicitar', 'publicidad', 'plan de', 'planifica',
        'promociona', 'difunde', 'difundir', 'visibilidad', 'destacar',
        'vender', 'anunciar', 'campaña', 'campana', 'posicionar',
        'impulsar', 'potenciar', 'contenido para', 'ideas para',
    }

    def __init__(self, property_db_service):
        super().__init__(callback_manager=CallbackManager([]))
        self.property_db_service = property_db_service
        self.user_id = None
        logger.info("✓ PropertyPromoEngine inicializado")

    def _is_promo_request(self, query: str) -> bool:
        q = query.lower()
        for kw in self.PROMO_KEYWORDS:
            if kw in q:
                return True
        words = q.split()
        for word in words:
            if len(word) <= 3:
                continue
            for kw in self.PROMO_KEYWORDS:
                if SequenceMatcher(None, word, kw).ratio() >= 0.75:
                    return True
        return False

    def _extract_property_id(self, query: str) -> Optional[int]:
        q = query.lower()
        patterns = [
            r'(?:id|propiedad|property|inmueble)\s*[:=]?\s*#?\s*(\d+)',
            r'#\s*(\d+)',
            r'\b(\d{2,6})\b',
        ]
        for pat in patterns:
            m = re.search(pat, q)
            if m:
                return int(m.group(1))
        return None

    def _get_platform_strategy(self, prop: Dict) -> Dict:
        """Determina las plataformas óptimas según el tipo y precio de la propiedad."""
        tipo = (prop.get('tipo_propiedad') or '').lower()
        precio_usd = float(prop.get('precio_usd') or 0)
        provincia = (prop.get('provincia') or '').lower()

        platforms = []
        primary = 'instagram'

        # Reglas por tipo
        if any(t in tipo for t in ['casa', 'apartamento', 'apto', 'residencia']):
            platforms = ['instagram', 'facebook', 'tiktok']
            primary = 'instagram'
        elif any(t in tipo for t in ['lote', 'terreno', 'finca']):
            platforms = ['facebook', 'instagram', 'youtube']
            primary = 'facebook'
        elif any(t in tipo for t in ['local', 'comercial', 'bodega', 'oficina']):
            platforms = ['linkedin', 'facebook', 'instagram']
            primary = 'linkedin'
        else:
            platforms = ['instagram', 'facebook']
            primary = 'instagram'

        # Ajuste por precio (propiedades altas → LinkedIn)
        if precio_usd > 300_000:
            if 'linkedin' not in platforms:
                platforms.insert(0, 'linkedin')
            primary = 'linkedin'

        # Zonas turísticas → TikTok prioritario
        zonas_turisticas = ['guanacaste', 'puntarenas', 'limon', 'quepos', 'tamarindo']
        if any(z in provincia for z in zonas_turisticas):
            if 'tiktok' not in platforms:
                platforms.insert(1, 'tiktok')

        return {'primary': primary, 'all': platforms}

    def _get_video_ideas(self, prop: Dict) -> list:
        """Genera ideas de video específicas según tipo y ubicación."""
        tipo = (prop.get('tipo_propiedad') or '').lower()
        provincia = (prop.get('provincia') or '').lower()
        canton = (prop.get('canton') or '').lower()
        bedrooms = prop.get('bedrooms')
        area = prop.get('area_construccion') or prop.get('tamanio_lote')

        ideas = []

        # Ideas base
        ideas.append(f"🎬 Tour virtual completo de la propiedad (30-60 seg, música dinámica)")
        ideas.append(f"📍 Video mostrando la ubicación: accesos, calle principal, referencia al comercio más cercano")

        # Por tipo
        if any(t in tipo for t in ['casa', 'apartamento']):
            ideas.append("🛏️ Recorrido por habitaciones con narración: 'Esta es la habitación principal...'")
            if bedrooms and int(bedrooms) >= 3:
                ideas.append("👨‍👩‍👧 Video lifestyle: familia disfrutando los espacios comunes")
        if any(t in tipo for t in ['lote', 'terreno', 'finca']):
            ideas.append("🌿 Drone shot del terreno completo mostrando los límites y naturaleza")
            ideas.append("🏗️ Video comparativo: 'Aquí podría quedar tu casa de sueños' con render o dibujo")
        if any(t in tipo for t in ['local', 'comercial']):
            ideas.append("💼 Video mostrando el flujo peatonal y vehicular del área")
            ideas.append("📊 Infográfico animado con el potencial de rentabilidad")

        # Por zona
        zonas_costa = ['guanacaste', 'puntarenas', 'limon', 'quepos']
        if any(z in provincia for z in zonas_costa):
            ideas.append("🌅 Reel al amanecer o atardecer aprovechando la luz natural costera")
            ideas.append("🌊 Video mostrando distancia a la playa y atractivos turísticos")

        if area:
            ideas.append(f"📐 Video enfatizando los {area} m² disponibles con comparación visual de espacios")

        return ideas

    def _get_hashtags(self, prop: Dict) -> str:
        tipo = (prop.get('tipo_propiedad') or 'propiedad').replace(' ', '')
        provincia = (prop.get('provincia') or '').replace(' ', '')
        canton = (prop.get('canton') or '').replace(' ', '')
        banco = (prop.get('nombre_banco') or '').replace(' ', '')

        tags = [
            f"#PropiedadesCostaRica",
            f"#BienesRaicesCR",
            f"#{tipo}EnVenta" if tipo else "#PropiedadEnVenta",
            f"#{provincia}" if provincia else "",
            f"#{canton}" if canton else "",
            "#BienesAdjudicados",
            "#RemateBancario",
            f"#{banco.replace('Banco','').strip()}CR" if banco else "",
            "#InversionInmobiliaria",
            "#CasaPropia",
        ]
        return " ".join(t for t in tags if t)

    def _build_prompt(self, prop: Dict, week_theme: Dict, platform_strategy: Dict,
                      video_ideas: list, hashtags: str) -> str:
        nombre = prop.get('nombre', 'Propiedad')
        tipo = prop.get('tipo_propiedad', 'Propiedad')
        ubicacion_parts = [p for p in [prop.get('distrito'), prop.get('canton'), prop.get('provincia')] if p]
        ubicacion = ', '.join(ubicacion_parts) or 'No especificada'
        precio = prop.get('precio_usd')
        precio_str = f"USD {float(precio):,.0f}" if precio else "No especificado"
        bedrooms = prop.get('bedrooms', '')
        bathrooms = prop.get('bathrooms', '')
        area_c = prop.get('area_construccion', '')
        area_l = prop.get('tamanio_lote', '')
        banco = prop.get('nombre_banco', 'No especificado')
        prop_url = prop.get('property_url', '')

        year, week = week_theme.get('year', ''), week_theme.get('week', '')

        video_ideas_text = "\n".join(f"  - {v}" for v in video_ideas)
        platforms_text = f"Principal: {platform_strategy['primary'].upper()} | Adicionales: {', '.join(platform_strategy['all'])}"

        prompt = f"""Eres Eva, asistente inmobiliaria estratégica. Tu tarea es generar un plan de promoción completo y personalizado para esta propiedad.

DATOS DE LA PROPIEDAD:
• Nombre: {nombre}
• Tipo: {tipo}
• Ubicación: {ubicacion}
• Precio: {precio_str}
• Habitaciones: {bedrooms or 'N/A'} | Baños: {bathrooms or 'N/A'}
• Área construcción: {area_c or 'N/A'} m² | Tamaño lote: {area_l or 'N/A'} m²
• Entidad bancaria: {banco}
• URL: {prop_url or 'No disponible'}

ESTRATEGIA DE PLATAFORMAS RECOMENDADAS:
{platforms_text}

ENFOQUE DE CONTENIDO ESTA SEMANA (Semana {week}/{year}):
• Tema: {week_theme['enfoque']}
• Descripción: {week_theme['descripcion']}
• Ángulo: {week_theme['angulo']}
• CTA sugerido: {week_theme['cta']}

IDEAS DE VIDEO DISPONIBLES:
{video_ideas_text}

HASHTAGS SUGERIDOS:
{hashtags}

Genera en español un plan de promoción estructurado con estas secciones:
1. **Análisis Estratégico de la Propiedad** (qué hace única a esta propiedad, sus USPs, audiencia objetivo)
2. **Plataformas Recomendadas** (para cada plataforma, explica POR QUÉ es la adecuada para esta propiedad)
3. **Plan de Contenido — Semana {week}** (basado en el enfoque de esta semana, da ideas concretas de posts, reels y stories)
4. **Ideas de Video Específicas** (usa las ideas de video proporcionadas y amplíalas con creatividad)
5. **Calendario Semanal Sugerido** (lunes a domingo, qué publicar cada día y en qué plataforma)
6. **Hashtags y Audiencia** (hashtags listos para usar + descripción del buyer persona)
7. **Próxima Semana** (anticipa el tema de la semana que viene)

Sé específico, creativo y práctico. El plan debe poder ejecutarse de inmediato.
"""
        return prompt

    def _query(self, query_bundle: QueryBundle) -> Response:
        query = query_bundle.query_str
        logger.info(f"🏠 PropertyPromoEngine recibió: {query}")

        property_id = self._extract_property_id(query)
        if not property_id:
            return Response(response=(
                "Para generar la estrategia de promoción necesito el **ID de la propiedad**.\n\n"
                "Ejemplo: *'Eva, dame una estrategia de promoción para el ID 150'*"
            ))

        # Verificar si es notificación semanal (no hay query explícita de estrategia)
        is_explicit = self._is_promo_request(query)
        if not is_explicit:
            # Intentar notificación semanal
            notif = get_weekly_notification_message(property_id)
            if notif:
                return Response(response=notif)

        # Obtener datos de la propiedad
        prop = self.property_db_service.get_property_by_id(property_id)
        if not prop:
            return Response(response=f"⚠️ No encontré la propiedad con ID **{property_id}** en la base de datos.")

        logger.info(f"✅ Propiedad encontrada: {prop.get('nombre')} (ID {property_id})")

        week_theme = get_week_theme(property_id)
        platform_strategy = self._get_platform_strategy(prop)
        video_ideas = self._get_video_ideas(prop)
        hashtags = self._get_hashtags(prop)

        prompt = self._build_prompt(prop, week_theme, platform_strategy, video_ideas, hashtags)

        try:
            llm = Settings.llm
            plan_text = llm.complete(prompt).text
        except Exception as e:
            logger.error(f"❌ Error en LLM: {e}")
            plan_text = f"Error generando el plan: {e}"

        # Guardar en historial
        log_strategy_generated(property_id, user_id=self.user_id)

        next_theme = get_next_week_theme(property_id)
        year, week = week_theme.get('year', ''), week_theme.get('week', '')

        response_text = (
            f"## 🏠 Estrategia de Promoción — {prop.get('nombre', f'Propiedad #{property_id}')}\n"
            f"*Semana {week}/{year} · Enfoque: {week_theme['enfoque']}*\n\n"
            f"{plan_text}\n\n"
            f"---\n"
            f"📅 **La próxima semana** el enfoque será: **{next_theme['enfoque']}** — "
            f"pídemelo y generaré un plan diferente.\n\n"
            f"¿Querés que genere también los textos de los posts listos para publicar? 💬"
        )

        return Response(response=response_text)

    async def _aquery(self, query_bundle: QueryBundle) -> Response:
        return self._query(query_bundle)

    def set_user_id(self, user_id: int):
        self.user_id = user_id

    def _get_prompt_modules(self):
        return {}
