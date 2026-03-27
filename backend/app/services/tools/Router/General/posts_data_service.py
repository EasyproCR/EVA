"""
Posts Data Service - Construye y procesa consultas de posts/publicaciones en redes sociales
"""

import logging
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from sqlalchemy import text

logger = logging.getLogger(__name__)


class PostsDataService:
    """
    Servicio para procesar consultas sobre posts/publicaciones:
    - Clasifica preguntas naturales sobre posts
    - Construye queries SQL a campaign_socials
    - Formatea respuestas legibles
    """

    # Keywords por categoría
    POSTS_KEYWORDS = {
        'post', 'posts', 'publicación', 'publicaciones', 'social', 'sociales',
        'instagram', 'facebook', 'twitter', 'tiktok', 'linkedin', 'youtube',
        'red social', 'redes sociales', 'reel', 'reels', 'feed', 'story', 'stories',
        'contenido', 'publicar', 'publicado', 'trending', 'engagement', 'reach'
    }

    REACTIONS_KEYWORDS = {'reacción', 'reacciones', 'likes', 'like', 'reacciona', 'engagement'}

    COMMENTS_KEYWORDS = {'comentario', 'comentarios', 'comenta', 'menciones', 'replies'}

    SHARES_KEYWORDS = {'compartir', 'compartido', 'share', 'shares', 'virales', 'viral'}

    VIEWS_KEYWORDS = {'vista', 'vistas', 'visualización', 'visualizaciones', 'view', 'reach'}

    PLATFORM_KEYWORDS = {
        'instagram': {'instagram', 'ig'},
        'facebook': {'facebook', 'fb'},
        'twitter': {'twitter', 'x'},
        'tiktok': {'tiktok', 'tt'},
        'linkedin': {'linkedin'},
        'youtube': {'youtube', 'yt'}
    }

    TOP_POSTS_KEYWORDS = {'mejores', 'mejor', 'top', 'trending', 'popular', 'virales', 'viral', 'más vistas'}

    def __init__(self, sql_database=None):
        """
        Args:
            sql_database: SQLDatabase instance from LlamaIndex
        """
        self.sql_database = sql_database
        logger.info("✓ PostsDataService inicializado")

    def process_query(self, query: str, user_roles: List[str]) -> str:
        """
        Procesa una consulta sobre posts y retorna respuesta formateada

        Args:
            query: Pregunta del usuario
            user_roles: Roles del usuario (para logging)

        Returns:
            Respuesta formateada en markdown
        """
        if not self.sql_database:
            logger.error("❌ SQL Database no configurada en PostsDataService")
            return "⚠️ Servicio de posts no disponible temporalmente. Por favor, intenta más tarde."

        try:
            # Clasificar tipo de consulta
            query_type = self._classify_query(query)
            logger.info(f"  📊 Tipo de consulta: {query_type}")

            # Procesar según tipo
            if query_type == "ALL_POSTS":
                return self._get_all_posts(query, user_roles)
            elif query_type == "PLATFORM_FILTER":
                return self._get_posts_by_platform(query, user_roles)
            elif query_type == "TOP_POSTS":
                return self._get_top_posts(query, user_roles)
            elif query_type == "STATS":
                return self._get_posts_stats(query, user_roles)
            elif query_type == "BY_ENGAGEMENT":
                return self._get_posts_by_engagement(query, user_roles)
            else:
                return "❓ No pude clasificar tu pregunta sobre posts. ¿Podrías ser más específico?"

        except Exception as e:
            logger.error(f"❌ Error procesando query de posts: {str(e)[:150]}", exc_info=True)
            return f"⚠️ Error al procesar tu consulta: {str(e)[:100]}"

    def _classify_query(self, query: str) -> Optional[str]:
        """
        Clasifica la pregunta en categoría usando keywords
        """
        query_lower = query.lower()

        # Detectar si es verdaderamente una pregunta sobre posts
        if not any(kw in query_lower for kw in self.POSTS_KEYWORDS):
            return None

        # Clasificar por tipo específico
        if any(kw in query_lower for kw in self.TOP_POSTS_KEYWORDS):
            return "TOP_POSTS"

        # Detectar filtro por plataforma
        for platform, keywords in self.PLATFORM_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                return "PLATFORM_FILTER"

        # Detectar preguntas de estadísticas
        if any(keyword in query_lower for keyword in ['promedio', 'promedio', 'total', 'cuántos', 'cuantos', 'estadística', 'estadisticas', 'resumen']):
            return "STATS"

        # Detectar preguntas sobre engagement
        engagement_keywords = self.REACTIONS_KEYWORDS | self.COMMENTS_KEYWORDS | self.SHARES_KEYWORDS | self.VIEWS_KEYWORDS
        if any(keyword in query_lower for keyword in engagement_keywords):
            return "BY_ENGAGEMENT"

        # Por defecto, retornar todos
        return "ALL_POSTS"

    def _get_all_posts(self, query: str, user_roles: List[str]) -> str:
        """Obtiene todos los posts/publicaciones"""
        try:
            sql = """
            SELECT
                cs.id,
                cs.platform,
                cs.language,
                cs.link,
                cs.reactions,
                cs.comments,
                cs.shares,
                cs.views,
                c.name as campaign_name,
                cs.created_at
            FROM campaign_socials cs
            JOIN campaigns c ON cs.campaign_id = c.id
            ORDER BY cs.created_at DESC
            LIMIT 20
            """

            results = self._execute_query(sql)

            if not results:
                return "📭 No hay posts registrados en el sistema."

            response = "📱 **PUBLICACIONES EN REDES SOCIALES**\n\n"
            for idx, row in enumerate(results, 1):
                platform_emoji = self._get_platform_emoji(row['platform'])
                response += f"{idx}. {platform_emoji} **{row['platform'].upper()}** - {row['campaign_name']}\n"
                response += f"   📝 [Ver post]({row['link']})\n"
                response += f"   ❤️ {row['reactions']} reacciones | 💬 {row['comments']} comentarios | "
                response += f"📤 {row['shares']} compartidos | 👁️ {row['views']} vistas\n"
                response += f"   🗓️ {row['created_at']}\n\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _get_all_posts: {str(e)}")
            return f"⚠️ Error obteniendo posts: {str(e)[:100]}"

    def _get_posts_by_platform(self, query: str, user_roles: List[str]) -> str:
        """Filtra posts por plataforma (Instagram, Facebook, etc.)"""
        try:
            query_lower = query.lower()
            platform = None

            for plat, keywords in self.PLATFORM_KEYWORDS.items():
                if any(kw in query_lower for kw in keywords):
                    platform = plat
                    break

            if not platform:
                return "❓ No identifiqué la plataforma. ¿Cuál era? (Instagram, Facebook, Twitter, TikTok, LinkedIn, YouTube)"

            sql = """
            SELECT
                cs.id,
                cs.platform,
                cs.language,
                cs.link,
                cs.reactions,
                cs.comments,
                cs.shares,
                cs.views,
                c.name as campaign_name,
                cs.created_at
            FROM campaign_socials cs
            JOIN campaigns c ON cs.campaign_id = c.id
            WHERE LOWER(cs.platform) = :platform
            ORDER BY cs.created_at DESC
            LIMIT 15
            """

            results = self._execute_query(sql, {'platform': platform.lower()})

            if not results:
                return f"📭 No hay posts en {platform} registrados."

            platform_emoji = self._get_platform_emoji(platform)
            response = f"{platform_emoji} **POSTS EN {platform.upper()}**\n\n"
            response += f"Se encontraron {len(results)} publicaciones:\n\n"

            for idx, row in enumerate(results, 1):
                response += f"{idx}. **{row['campaign_name']}** ({row['language'].upper()})\n"
                response += f"   📝 [Ver post]({row['link']})\n"
                response += f"   ❤️ {row['reactions']} | 💬 {row['comments']} | 📤 {row['shares']} | 👁️ {row['views']}\n\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _get_posts_by_platform: {str(e)}")
            return f"⚠️ Error filtrando posts: {str(e)[:100]}"

    def _get_top_posts(self, query: str, user_roles: List[str]) -> str:
        """Obtiene los posts con mejor rendimiento (más engagement)"""
        try:
            sql = """
            SELECT
                cs.id,
                cs.platform,
                cs.language,
                cs.link,
                cs.reactions,
                cs.comments,
                cs.shares,
                cs.views,
                c.name as campaign_name,
                (cs.reactions + cs.comments + cs.shares) as total_engagement,
                cs.created_at
            FROM campaign_socials cs
            JOIN campaigns c ON cs.campaign_id = c.id
            ORDER BY total_engagement DESC
            LIMIT 10
            """

            results = self._execute_query(sql)

            if not results:
                return "📭 No hay posts para analizar."

            response = "🏆 **TOP 10 POSTS CON MEJOR RENDIMIENTO**\n\n"

            for idx, row in enumerate(results, 1):
                platform_emoji = self._get_platform_emoji(row['platform'])
                response += f"{idx}. {platform_emoji} **{row['platform'].upper()}** - {row['campaign_name']}\n"
                response += f"   Engagement total: **{row['total_engagement']}** "
                response += f"(❤️ {row['reactions']} + 💬 {row['comments']} + 📤 {row['shares']})\n"
                response += f"   👁️ {row['views']} vistas | [Ver post]({row['link']})\n\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _get_top_posts: {str(e)}")
            return f"⚠️ Error obteniendo top posts: {str(e)[:100]}"

    def _get_posts_stats(self, query: str, user_roles: List[str]) -> str:
        """Obtiene estadísticas agregadas de todos los posts"""
        try:
            sql = """
            SELECT
                COUNT(*) as total_posts,
                SUM(reactions) as total_reactions,
                SUM(comments) as total_comments,
                SUM(shares) as total_shares,
                SUM(views) as total_views,
                AVG(reactions) as avg_reactions,
                AVG(comments) as avg_comments,
                AVG(shares) as avg_shares,
                AVG(views) as avg_views,
                MAX(reactions) as max_reactions,
                MAX(comments) as max_comments,
                MAX(shares) as max_shares,
                MAX(views) as max_views
            FROM campaign_socials
            """

            results = self._execute_query(sql)

            if not results:
                return "📭 No hay datos de posts."

            row = results[0]

            response = "📊 **ESTADÍSTICAS GENERALES DE POSTS**\n\n"
            response += f"**Total de publicaciones:** {int(row['total_posts']) or 0}\n\n"
            response += "**TOTALES:**\n"
            response += f"- ❤️ Reacciones: **{int(row['total_reactions']) or 0}**\n"
            response += f"- 💬 Comentarios: **{int(row['total_comments']) or 0}**\n"
            response += f"- 📤 Compartidos: **{int(row['total_shares']) or 0}**\n"
            response += f"- 👁️ Vistas: **{int(row['total_views']) or 0}**\n\n"

            response += "**PROMEDIOS POR POST:**\n"
            response += f"- ❤️ {float(row['avg_reactions'] or 0):.1f} reacciones\n"
            response += f"- 💬 {float(row['avg_comments'] or 0):.1f} comentarios\n"
            response += f"- 📤 {float(row['avg_shares'] or 0):.1f} compartidos\n"
            response += f"- 👁️ {float(row['avg_views'] or 0):.1f} vistas\n\n"

            response += "**MÁXIMOS ALCANZADOS:**\n"
            response += f"- ❤️ {int(row['max_reactions']) or 0} reacciones\n"
            response += f"- 💬 {int(row['max_comments']) or 0} comentarios\n"
            response += f"- 📤 {int(row['max_shares']) or 0} compartidos\n"
            response += f"- 👁️ {int(row['max_views']) or 0} vistas\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _get_posts_stats: {str(e)}")
            return f"⚠️ Error obteniendo estadísticas: {str(e)[:100]}"

    def _get_posts_by_engagement(self, query: str, user_roles: List[str]) -> str:
        """Filtra posts por tipo de engagement (likes, comentarios, shares, vistas)"""
        try:
            query_lower = query.lower()

            # Determinar qué campo consultar
            if any(kw in query_lower for kw in self.REACTIONS_KEYWORDS):
                order_field = "reactions"
                emoji = "❤️"
                label = "REACCIONES"
            elif any(kw in query_lower for kw in self.COMMENTS_KEYWORDS):
                order_field = "comments"
                emoji = "💬"
                label = "COMENTARIOS"
            elif any(kw in query_lower for kw in self.SHARES_KEYWORDS):
                order_field = "shares"
                emoji = "📤"
                label = "COMPARTIDOS"
            elif any(kw in query_lower for kw in self.VIEWS_KEYWORDS):
                order_field = "views"
                emoji = "👁️"
                label = "VISTAS"
            else:
                order_field = "reactions"
                emoji = "❤️"
                label = "REACCIONES"

            sql = f"""
            SELECT
                cs.id,
                cs.platform,
                cs.link,
                cs.reactions,
                cs.comments,
                cs.shares,
                cs.views,
                c.name as campaign_name
            FROM campaign_socials cs
            JOIN campaigns c ON cs.campaign_id = c.id
            WHERE {order_field} > 0
            ORDER BY {order_field} DESC
            LIMIT 12
            """

            results = self._execute_query(sql)

            if not results:
                return f"📭 No hay posts con {label.lower()}."

            response = f"{emoji} **TOP POSTS POR {label}**\n\n"

            for idx, row in enumerate(results, 1):
                platform_emoji = self._get_platform_emoji(row['platform'])
                engagement_value = row[order_field]
                response += f"{idx}. {platform_emoji} **{row[f'{order_field}']}** {emoji} - {row['campaign_name']}\n"
                response += f"   [Ver post]({row['link']})\n\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _get_posts_by_engagement: {str(e)}")
            return f"⚠️ Error filtrando por engagement: {str(e)[:100]}"

    def _execute_query(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        """Ejecuta query SQL y retorna resultados como lista de dicts"""
        try:
            if not self.sql_database:
                raise ValueError("SQL Database no configurada")

            connection = self.sql_database._engine.connect()

            if params:
                result = connection.execute(text(sql), params)
            else:
                result = connection.execute(text(sql))

            rows = result.fetchall()
            connection.close()

            return [dict(row._mapping) for row in rows]

        except Exception as e:
            logger.error(f"❌ Error ejecutando SQL: {str(e)}")
            raise

    def _get_platform_emoji(self, platform: str) -> str:
        """Retorna emoji para plataforma"""
        emoji_map = {
            'instagram': '📸',
            'facebook': '👍',
            'twitter': '🐦',
            'tiktok': '🎵',
            'linkedin': '💼',
            'youtube': '📹'
        }
        return emoji_map.get(platform.lower(), '📱')
