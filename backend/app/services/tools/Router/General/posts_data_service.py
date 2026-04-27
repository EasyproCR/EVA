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

    REACH_KEYWORDS = {'alcance', 'reach', 'cobertura', 'impresiones', 'impression', 'personas alcanzadas', 'audiencia'}

    COMPARISON_KEYWORDS = {'comparar', 'comparación', 'vs', 'versus', 'diferencia', 'entre', 'comparativa', 'cuál mejor', 'cual mejor'}

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
            if query_type == "URL_SPECIFIC":
                return self._get_post_by_url(query)
            elif query_type == "ALL_POSTS":
                return self._get_all_posts(query, user_roles)
            elif query_type == "PLATFORM_FILTER":
                return self._get_posts_by_platform(query, user_roles)
            elif query_type == "TOP_POSTS":
                return self._get_top_posts(query, user_roles)
            elif query_type == "STATS":
                return self._get_posts_stats(query, user_roles)
            elif query_type == "BY_ENGAGEMENT":
                return self._get_posts_by_engagement(query, user_roles)
            elif query_type == "REACH":
                return self._get_posts_reach(query, user_roles)
            elif query_type == "REACH_COMPARISON":
                return self._get_posts_reach_comparison(query, user_roles)
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

        # PRIORIDAD 1: Detectar si contiene una URL específica
        if self._extract_url_from_query(query):
            return "URL_SPECIFIC"

        # Detectar comparativas de alcance primero (tiene prioridad)
        if any(kw in query_lower for kw in self.REACH_KEYWORDS) and any(kw in query_lower for kw in self.COMPARISON_KEYWORDS):
            return "REACH_COMPARISON"

        # Detectar preguntas sobre alcance (reach)
        if any(kw in query_lower for kw in self.REACH_KEYWORDS):
            return "REACH"

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

    def _get_posts_reach(self, query: str, user_roles: List[str]) -> str:
        """Calcula y muestra el alcance (reach/vistas) de las publicaciones"""
        try:
            query_lower = query.lower()

            # Detectar si es por plataforma específica
            platform = None
            for plat, keywords in self.PLATFORM_KEYWORDS.items():
                if any(kw in query_lower for kw in keywords):
                    platform = plat
                    break

            if platform:
                # Alcance por plataforma específica
                sql = """
                SELECT
                    cs.platform,
                    c.name as campaign_name,
                    cs.views,
                    cs.reactions,
                    cs.comments,
                    cs.shares,
                    SUM(cs.views) OVER (PARTITION BY cs.platform) as platform_total_reach,
                    cs.created_at
                FROM campaign_socials cs
                JOIN campaigns c ON cs.campaign_id = c.id
                WHERE LOWER(cs.platform) = :platform
                ORDER BY cs.views DESC
                LIMIT 20
                """
                results = self._execute_query(sql, {'platform': platform.lower()})
            else:
                # Alcance total de todas las plataformas
                sql = """
                SELECT
                    cs.platform,
                    c.name as campaign_name,
                    cs.views,
                    cs.reactions,
                    cs.comments,
                    cs.shares,
                    cs.created_at
                FROM campaign_socials cs
                JOIN campaigns c ON cs.campaign_id = c.id
                ORDER BY cs.views DESC
                LIMIT 25
                """
                results = self._execute_query(sql)

            if not results:
                return "📭 No hay datos de alcance disponibles."

            # Calcular totales
            total_reach = sum(int(row['views'] or 0) for row in results)
            avg_reach = total_reach / len(results) if results else 0
            max_reach = max(int(row['views'] or 0) for row in results) if results else 0

            platform_emoji = self._get_platform_emoji(platform) if platform else "📱"
            title = f"{platform_emoji} **ALCANCE EN {platform.upper()}**" if platform else "📊 **ALCANCE TOTAL DE PUBLICACIONES**"

            response = f"{title}\n\n"
            response += f"**Alcance total:** 👁️ **{total_reach:,}** vistas\n"
            response += f"**Alcance promedio:** {avg_reach:,.0f} vistas por post\n"
            response += f"**Alcance máximo:** {max_reach:,} vistas\n"
            response += f"**Total de posts:** {len(results)}\n\n"

            response += "**DETALLE POR PUBLICACIÓN:**\n\n"

            for idx, row in enumerate(results, 1):
                if idx > 15:  # Limitar a 15 items en el resumen
                    remaining = len(results) - 15
                    response += f"\n... y {remaining} publicaciones más"
                    break

                plat_emoji = self._get_platform_emoji(row['platform'])
                views = int(row['views'] or 0)
                reactions = int(row['reactions'] or 0)
                comments = int(row['comments'] or 0)
                shares = int(row['shares'] or 0)

                response += f"{idx}. {plat_emoji} **{row['platform'].upper()}** - {row['campaign_name']}\n"
                response += f"   👁️ **{views:,}** vistas | ❤️ {reactions} | 💬 {comments} | 📤 {shares}\n"
                response += f"   📅 {row['created_at']}\n\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _get_posts_reach: {str(e)}")
            return f"⚠️ Error obteniendo alcance: {str(e)[:100]}"

    def _get_posts_reach_comparison(self, query: str, user_roles: List[str]) -> str:
        """Compara alcance entre plataformas, campañas o períodos"""
        try:
            query_lower = query.lower()

            # Detectar si es comparativa entre plataformas
            mentioned_platforms = []
            for plat, keywords in self.PLATFORM_KEYWORDS.items():
                if any(kw in query_lower for kw in keywords):
                    mentioned_platforms.append(plat)

            if len(mentioned_platforms) >= 2:
                # Comparativa específica entre plataformas mencionadas
                return self._compare_platforms(mentioned_platforms, user_roles)
            elif len(mentioned_platforms) == 1:
                # Comparar una plataforma contra el promedio general
                return self._compare_platform_vs_average(mentioned_platforms[0], user_roles)
            else:
                # Comparativa general entre todas las plataformas
                return self._compare_all_platforms(user_roles)

        except Exception as e:
            logger.error(f"❌ Error en _get_posts_reach_comparison: {str(e)}")
            return f"⚠️ Error en comparativa de alcance: {str(e)[:100]}"

    def _compare_platforms(self, platforms: List[str], user_roles: List[str]) -> str:
        """Compara alcance entre plataformas específicas"""
        try:
            platform_list = ', '.join([f"'{p.lower()}'" for p in platforms])

            sql = f"""
            SELECT
                LOWER(cs.platform) as platform,
                COUNT(*) as total_posts,
                SUM(cs.views) as total_reach,
                AVG(cs.views) as avg_reach,
                MAX(cs.views) as max_reach,
                SUM(cs.reactions) as total_reactions,
                SUM(cs.comments) as total_comments,
                SUM(cs.shares) as total_shares
            FROM campaign_socials cs
            WHERE LOWER(cs.platform) IN ({platform_list})
            GROUP BY LOWER(cs.platform)
            ORDER BY SUM(cs.views) DESC
            """

            results = self._execute_query(sql)

            if not results or len(results) < 2:
                return "📭 No hay suficientes datos para comparar."

            response = "📊 **COMPARATIVA DE ALCANCE ENTRE PLATAFORMAS**\n\n"

            # Tabla comparativa
            response += "| Plataforma | Posts | Alcance Total | Alcance Promedio | Máximo |\n"
            response += "|---|---|---|---|---|\n"

            max_reach_value = max(int(row['total_reach'] or 0) for row in results)

            for row in results:
                platform = row['platform'].upper()
                total = int(row['total_posts'] or 0)
                reach = int(row['total_reach'] or 0)
                avg = int(row['avg_reach'] or 0)
                max_val = int(row['max_reach'] or 0)

                # Indicador de desempeño
                if reach == max_reach_value:
                    indicator = "🏆"
                else:
                    percentage = (reach / max_reach_value * 100) if max_reach_value > 0 else 0
                    indicator = "📈" if percentage > 75 else "📊"

                response += f"| {indicator} {platform} | {total} | {reach:,} | {avg:,} | {max_val:,} |\n"

            # Análisis detallado
            response += "\n**ANÁLISIS DETALLADO:**\n\n"

            sorted_results = sorted(results, key=lambda x: int(x['total_reach'] or 0), reverse=True)

            for idx, row in enumerate(sorted_results, 1):
                platform = row['platform'].upper()
                reach = int(row['total_reach'] or 0)
                reactions = int(row['total_reactions'] or 0)
                comments = int(row['total_comments'] or 0)
                shares = int(row['total_shares'] or 0)

                response += f"{idx}. **{platform}**\n"
                response += f"   👁️ Alcance: **{reach:,}** vistas\n"
                response += f"   ❤️ {reactions} reacciones | 💬 {comments} comentarios | 📤 {shares} compartidos\n\n"

            # Recomendación
            best_platform = sorted_results[0]['platform'].upper()
            worst_platform = sorted_results[-1]['platform'].upper()
            best_reach = int(sorted_results[0]['total_reach'] or 0)
            worst_reach = int(sorted_results[-1]['total_reach'] or 0)
            difference = best_reach - worst_reach

            response += f"**💡 INSIGHT:** {best_platform} lidera con {best_reach:,} vistas, "
            response += f"**{difference:,}** vistas más que {worst_platform}.\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _compare_platforms: {str(e)}")
            return f"⚠️ Error comparando plataformas: {str(e)[:100]}"

    def _compare_platform_vs_average(self, platform: str, user_roles: List[str]) -> str:
        """Compara una plataforma contra el promedio general"""
        try:
            sql = """
            SELECT
                LOWER(cs.platform) as platform,
                COUNT(*) as total_posts,
                SUM(cs.views) as total_reach,
                AVG(cs.views) as avg_reach
            FROM campaign_socials cs
            GROUP BY LOWER(cs.platform)
            """

            results = self._execute_query(sql)

            if not results:
                return "📭 No hay datos disponibles."

            # Encontrar datos de la plataforma específica
            platform_data = None
            total_reach_all = sum(int(row['total_reach'] or 0) for row in results)
            total_posts_all = sum(int(row['total_posts'] or 0) for row in results)
            avg_reach_all = total_reach_all / total_posts_all if total_posts_all > 0 else 0

            for row in results:
                if row['platform'].lower() == platform.lower():
                    platform_data = row
                    break

            if not platform_data:
                return f"❓ No hay datos para {platform}."

            platform_reach = int(platform_data['total_reach'] or 0)
            platform_avg = int(platform_data['avg_reach'] or 0)
            platform_posts = int(platform_data['total_posts'] or 0)

            # Calcular diferencia
            diff = platform_reach - total_reach_all
            diff_percentage = (diff / total_reach_all * 100) if total_reach_all > 0 else 0
            avg_diff = platform_avg - avg_reach_all
            avg_diff_percentage = (avg_diff / avg_reach_all * 100) if avg_reach_all > 0 else 0

            response = f"📊 **{platform.upper()} vs PROMEDIO GENERAL**\n\n"

            response += f"| Métrica | {platform.upper()} | Promedio General | Diferencia |\n"
            response += "|---|---|---|---|\n"
            response += f"| Alcance Total | {platform_reach:,} | {int(total_reach_all):,} | {diff:+,} ({diff_percentage:+.1f}%) |\n"
            response += f"| Alcance Promedio/Post | {platform_avg:,} | {int(avg_reach_all):,} | {avg_diff:+,} ({avg_diff_percentage:+.1f}%) |\n"
            response += f"| Total Posts | {platform_posts} | {total_posts_all} | - |\n\n"

            if diff > 0:
                response += f"✅ {platform.upper()} supera el promedio en **{abs(diff):,}** vistas "
                response += f"({diff_percentage:+.1f}% más que el promedio).\n"
            else:
                response += f"⚠️ {platform.upper()} está por debajo del promedio en **{abs(diff):,}** vistas "
                response += f"({diff_percentage:.1f}% menos que el promedio).\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _compare_platform_vs_average: {str(e)}")
            return f"⚠️ Error en comparativa: {str(e)[:100]}"

    def _compare_all_platforms(self, user_roles: List[str]) -> str:
        """Compara todas las plataformas"""
        try:
            sql = """
            SELECT
                LOWER(cs.platform) as platform,
                COUNT(*) as total_posts,
                SUM(cs.views) as total_reach,
                AVG(cs.views) as avg_reach,
                MAX(cs.views) as max_reach,
                SUM(cs.reactions) as total_reactions,
                SUM(cs.comments) as total_comments,
                SUM(cs.shares) as total_shares
            FROM campaign_socials cs
            GROUP BY LOWER(cs.platform)
            ORDER BY SUM(cs.views) DESC
            """

            results = self._execute_query(sql)

            if not results:
                return "📭 No hay datos de plataformas."

            response = "📊 **COMPARATIVA GENERAL DE ALCANCE**\n\n"

            # Tabla comparativa
            response += "| # | Plataforma | Posts | Alcance Total | Promedio | Máximo |\n"
            response += "|---|---|---|---|---|---|\n"

            total_reach_all = sum(int(row['total_reach'] or 0) for row in results)

            for idx, row in enumerate(results, 1):
                platform = row['platform'].upper()
                posts = int(row['total_posts'] or 0)
                reach = int(row['total_reach'] or 0)
                avg = int(row['avg_reach'] or 0)
                max_val = int(row['max_reach'] or 0)
                percentage = (reach / total_reach_all * 100) if total_reach_all > 0 else 0

                emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "•"
                response += f"| {emoji} | {platform} | {posts} | {reach:,} ({percentage:.1f}%) | {avg:,} | {max_val:,} |\n"

            response += f"\n**Alcance Total General:** 👁️ **{total_reach_all:,}** vistas\n"

            return response

        except Exception as e:
            logger.error(f"❌ Error en _compare_all_platforms: {str(e)}")
            return f"⚠️ Error comparando plataformas: {str(e)[:100]}"

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
