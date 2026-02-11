catalog_bienes = {
 "vw_get_all_properties": """
 Inventario de bienes adjudicados disponibles.

 Contiene propiedades recuperadas por entidades financieras.

 Columnas importantes:
 - nombre: nombre de la propiedad
 - provincia, canton, distrito: ubicación geográfica
 - precio_usd, precio_local: precios
 - tipo_propiedad: categoría del inmueble
 - bedrooms, bathrooms
 - area_construccion
 - tamano_lote
 - nombre_banco: entidad propietaria
 - tipo_oferta: modalidad (venta directa, subasta, etc)

 Reglas:
 - Siempre usar SELECT.
 - Para listados usar LIMIT 20.
 - Filtrar por provincia/canton cuando sea posible.
 """
}
