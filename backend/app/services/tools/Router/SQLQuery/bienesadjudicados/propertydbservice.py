"""
Property Database Service - Consulta propiedades individuales desde la BD
Proporciona datos estructurados para complementar información web
"""

import re
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)


class PropertyDatabaseService:
    """
    Servicio para consultar propiedades específicas desde la base de datos.
    Usado para obtener datos que Tavily no puede extraer de la web.
    """
    
    def __init__(self, connection_uri: str):
        """
        Args:
            connection_uri: URI de conexión a la BD de bienes
        """
        self.engine = create_engine(
            connection_uri,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        logger.info("✓ PropertyDatabaseService inicializado")
    
    def get_property_by_url(self, property_url: str) -> Optional[Dict[str, Any]]:
        """
        Busca una propiedad por su URL completa.
        
        Args:
            property_url: URL de la propiedad (ej: https://bienesadjudicadoscr.com/propiedades/casa-123)
            
        Returns:
            Dict con datos de la propiedad o None si no se encuentra
        """
        try:
            # Extraer slug de la URL
            slug = self._extract_slug_from_url(property_url)
            
            if not slug:
                logger.warning(f"⚠️ No se pudo extraer slug de URL: {property_url}")
                return None
            
            logger.info(f"🔍 Buscando propiedad por slug: {slug}")
            
            # Query para buscar por URL
            query = text("""
                SELECT 
                    nombre,
                    provincia,
                    canton,
                    distrito,
                    precio_usd,
                    precio_local,
                    tipo_propiedad,
                    bedrooms,
                    bathrooms,
                    area_construccion,
                    tamanio_lote,
                    nombre_banco,
                    tipo_oferta,
                    agent_name,
                    agent_phone_number,
                    property_url
                FROM vw_get_all_properties
                WHERE property_url LIKE :url_pattern
                LIMIT 1
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(
                    query,
                    {"url_pattern": f"%{slug}%"}
                )
                row = result.fetchone()
                
                if row:
                    # Convertir a diccionario
                    property_data = {
                        'nombre': row[0],
                        'provincia': row[1],
                        'canton': row[2],
                        'distrito': row[3],
                        'precio_usd': row[4],
                        'precio_local': row[5],
                        'tipo_propiedad': row[6],
                        'bedrooms': row[7],
                        'bathrooms': row[8],
                        'area_construccion': row[9],
                        'tamanio_lote': row[10],
                        'nombre_banco': row[11],
                        'tipo_oferta': row[12],
                        'agent_name': row[13],
                        'agent_phone_number': row[14],
                        'property_url': row[15],
                    
                    }
                    
                    logger.info(f"✓ Propiedad encontrada en BD: {property_data['nombre']}")
                    return property_data
                else:
                    logger.warning(f"⚠️ Propiedad no encontrada en BD para slug: {slug}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error consultando BD: {e}", exc_info=True)
            return None
    
    def get_property_by_name(self, property_name: str) -> Optional[Dict[str, Any]]:
        """
        Busca una propiedad por nombre aproximado.
        
        Args:
            property_name: Nombre de la propiedad
            
        Returns:
            Dict con datos de la propiedad o None
        """
        try:
            logger.info(f"🔍 Buscando propiedad por nombre: {property_name}")
            
            query = text("""
                SELECT 
                    nombre,
                    provincia,
                    canton,
                    distrito,
                    precio_usd,
                    precio_local,
                    tipo_propiedad,
                    bedrooms,
                    bathrooms,
                    area_construccion,
                    tamanio_lote,
                    nombre_banco,
                    tipo_oferta,
                    agent_name,
                    agent_phone_number,
                    property_url,
                    descripcion
                FROM vw_get_all_properties
                WHERE nombre LIKE :name_pattern
                LIMIT 1
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(
                    query,
                    {"name_pattern": f"%{property_name}%"}
                )
                row = result.fetchone()
                
                if row:
                    property_data = {
                        'nombre': row[0],
                        'provincia': row[1],
                        'canton': row[2],
                        'distrito': row[3],
                        'precio_usd': row[4],
                        'precio_local': row[5],
                        'tipo_propiedad': row[6],
                        'bedrooms': row[7],
                        'bathrooms': row[8],
                        'area_construccion': row[9],
                        'tamanio_lote': row[10],
                        'nombre_banco': row[11],
                        'tipo_oferta': row[12],
                        'agent_name': row[13],
                        'agent_phone_number': row[14],
                        'property_url': row[15],
                        'descripcion': row[16],
                    }
                    
                    logger.info(f"✓ Propiedad encontrada: {property_data['nombre']}")
                    return property_data
                else:
                    logger.warning(f"⚠️ Propiedad no encontrada: {property_name}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error consultando BD: {e}", exc_info=True)
            return None

    def get_property_by_id(self, property_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca una propiedad por su ID de base de datos.

        Args:
            property_id: ID único de la propiedad en la BD

        Returns:
            Dict con datos de la propiedad o None si no se encuentra
        """
        try:
            logger.info(f"🔍 Buscando propiedad por ID: {property_id}")

            query = text("""
                SELECT
                    nombre,
                    provincia,
                    canton,
                    distrito,
                    precio_usd,
                    precio_local,
                    tipo_propiedad,
                    bedrooms,
                    bathrooms,
                    area_construccion,
                    tamanio_lote,
                    nombre_banco,
                    tipo_oferta,
                    agent_name,
                    agent_phone_number,
                    property_url,
                    id
                FROM vw_get_all_properties
                WHERE id = :property_id
                LIMIT 1
            """)

            with self.engine.connect() as conn:
                result = conn.execute(
                    query,
                    {"property_id": property_id}
                )
                row = result.fetchone()

                if row:
                    property_data = {
                        'nombre': row[0],
                        'provincia': row[1],
                        'canton': row[2],
                        'distrito': row[3],
                        'precio_usd': row[4],
                        'precio_local': row[5],
                        'tipo_propiedad': row[6],
                        'bedrooms': row[7],
                        'bathrooms': row[8],
                        'area_construccion': row[9],
                        'tamanio_lote': row[10],
                        'nombre_banco': row[11],
                        'tipo_oferta': row[12],
                        'agent_name': row[13],
                        'agent_phone_number': row[14],
                        'property_url': row[15],
                        'id': row[16],
                    }

                    logger.info(f"✓ Propiedad encontrada en BD: {property_data['nombre']} (ID: {property_id})")
                    return property_data
                else:
                    logger.warning(f"⚠️ Propiedad no encontrada en BD para ID: {property_id}")
                    return None

        except Exception as e:
            logger.error(f"❌ Error consultando BD: {e}", exc_info=True)
            return None

    def _extract_slug_from_url(self, url: str) -> Optional[str]:
        """
        Extrae el slug de una URL de propiedad.
        
        Args:
            url: URL completa (ej: https://bienesadjudicadoscr.com/propiedades/casa-cartago-123)
            
        Returns:
            Slug (ej: casa-cartago-123) o None
        """
        try:
            parsed = urlparse(url)
            path = parsed.path
            
            # Limpiar el path
            path = path.strip('/')
            
            # Tomar la última parte (el slug)
            parts = path.split('/')
            if parts:
                slug = parts[-1]
                slug = unquote(slug)  # Decodificar URL encoding
                return slug
            
            return None
            
        except Exception as e:
            logger.error(f"Error extrayendo slug: {e}")
            return None
    
    def format_property_data_for_llm(self, property_data: Dict[str, Any]) -> str:
        """
        Formatea datos de propiedad para que el LLM los use.
        
        Args:
            property_data: Diccionario con datos de la propiedad
            
        Returns:
            Texto formateado con los datos
        """
        if not property_data:
            return ""
        
        lines = ["DATOS DE LA BASE DE DATOS:\n"]
        
        # Información básica
        if property_data.get('nombre'):
            lines.append(f"• Nombre: {property_data['nombre']}")
        
        # Ubicación
        ubicacion_parts = []
        if property_data.get('distrito'):
            ubicacion_parts.append(property_data['distrito'])
        if property_data.get('canton'):
            ubicacion_parts.append(property_data['canton'])
        if property_data.get('provincia'):
            ubicacion_parts.append(property_data['provincia'])
        
        if ubicacion_parts:
            lines.append(f"• Ubicación: {', '.join(ubicacion_parts)}")
        
        # Precio
        if property_data.get('precio_usd'):
            precio_formatted = f"USD {float(property_data['precio_usd']):,.0f}"
            lines.append(f"• Precio: {precio_formatted}")
        elif property_data.get('precio_local'):
            lines.append(f"• Precio local: {float(property_data['precio_local']):,.0f}")
        
        # Características
        if property_data.get('tipo_propiedad'):
            lines.append(f"• Tipo: {property_data['tipo_propiedad']}")
        
        if property_data.get('bedrooms'):
            lines.append(f"• Habitaciones: {property_data['bedrooms']}")
        
        if property_data.get('bathrooms'):
            lines.append(f"• Baños: {property_data['bathrooms']}")
        
        if property_data.get('area_construccion'):
            lines.append(f"• Área construcción: {property_data['area_construccion']} m²")
        
        if property_data.get('tamanio_lote'):
            lines.append(f"• Tamaño lote: {property_data['tamanio_lote']} m²")
        
        # Información institucional (LO MÁS IMPORTANTE)
        if property_data.get('nombre_banco'):
            lines.append(f"• **Banco/Entidad**: {property_data['nombre_banco']}")
        
        if property_data.get('tipo_oferta'):
            lines.append(f"• Tipo de oferta: {property_data['tipo_oferta']}")
        
        # Agente
        if property_data.get('agent_name'):
            lines.append(f"• **Agente a cargo**: {property_data['agent_name']}")
            
            if property_data.get('agent_phone_number'):
                lines.append(f"• **Teléfono del agente**: {property_data['agent_phone_number']}")
        
        return "\n".join(lines)


# ============================================================================
# INSTANCIA GLOBAL (Lazy initialization)
# ============================================================================

_property_db_service = None


def get_property_db_service(connection_uri: str = None) -> PropertyDatabaseService:
    """
    Obtiene instancia global del servicio de BD.
    
    Args:
        connection_uri: URI de conexión (solo necesario la primera vez)
        
    Returns:
        PropertyDatabaseService instance
    """
    global _property_db_service
    
    if _property_db_service is None:
        if connection_uri is None:
            raise ValueError("connection_uri requerido en primera llamada")
        _property_db_service = PropertyDatabaseService(connection_uri)
    
    return _property_db_service


# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================

def get_property_data_by_url(
    property_url: str,
    connection_uri: str = None
) -> Optional[Dict[str, Any]]:
    """
    Obtiene datos de propiedad por URL.
    
    Args:
        property_url: URL de la propiedad
        connection_uri: URI de BD (opcional si ya se inicializó)
        
    Returns:
        Dict con datos o None
    """
    service = get_property_db_service(connection_uri)
    return service.get_property_by_url(property_url)


def format_property_data(property_data: Dict[str, Any]) -> str:
    """Formatea datos de propiedad para el LLM."""
    service = get_property_db_service()
    return service.format_property_data_for_llm(property_data)


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test con URL de ejemplo
    test_url = "https://bienesadjudicadoscr.com/propiedades/casa-en-el-carmen-cartago"
    
    # Necesitarías la connection_uri real para probar
    # service = PropertyDatabaseService("mysql+pymysql://user:pass@host/db")
    # data = service.get_property_by_url(test_url)
    # 
    # if data:
    #     print("\n" + "="*80)
    #     print("DATOS ENCONTRADOS:")
    #     print("="*80)
    #     print(service.format_property_data_for_llm(data))
    # else:
    #     print("No se encontró la propiedad")
    
    # Test de extracción de slug
    service = PropertyDatabaseService("dummy://")
    slug = service._extract_slug_from_url(test_url)
    print(f"\nSlug extraído: {slug}")