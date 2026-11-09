"""Mapa único plantilla -> motivos permitidos.

Fuente de verdad compartida por el AJAX de motivos (views/ajax.py) y la
validación del formulario (forms.TramiteForm.clean). Así el servidor nunca
acepta un motivo que la plantilla no ofrece.

Convenciones:
- Lista con ids = solo esos motivos valen.
- Lista vacía [] = la plantilla NO lleva motivo (ej. CAPTURA DE GRAVIDEZ).
- None = plantilla desconocida: no se valida (legado) para no romper flujos.
"""

MOTIVOS_POR_PLANTILLA = {
    "REINGRESO": [1, 2, 3, 4, 5, 6, 7, 21, 22, 24, 38, 40],
    "FILIACION": [1, 2, 3, 4, 5, 6, 7, 21, 22, 24, 38, 40],
    "SOLICITUD DE ASIGNACION": [1, 2, 3, 4, 5, 6, 7, 21, 22, 24, 38, 40],
    "REINGRESO SIN PRELACION": [1, 2, 3, 4, 5, 6, 7, 21, 22, 24, 38, 40],
    "JUSTIFICACION DE PERFIL": [1, 2, 3, 4, 5, 6, 7, 21, 22, 24, 38, 40],
    "REPORTE DE VACANCIA": [1, 2, 3, 4, 5, 6, 7, 21, 22, 24, 38, 40],
    "CONSTANCIAS": [20, 23, 29, 30, 31, 32, 33, 34, 35, 36, 37],
    "CAMBIO DEL CENTRO DE TRABAJO": [19, 13],
    "CUADRO CAMBIOS CON FOLIO": [13],
    "PROPUESTA DE MOVIMIENTO": [11, 12, 25, 26, 27],
    "ALTA INICIAL (09)": [39],
    "OFICIO DE REINCORPORACION": [1, 2, 4, 15, 21, 22, 24, 40],
    "PRESENTACION LABORAL": [1, 2, 3, 4, 5, 6, 7, 21, 22, 24, 40],
    "PRESENTACION LABORAL PARA CAMBIO DE ADSCRIPCION": [1, 2, 3, 4, 5, 6, 7, 21, 22, 24, 40],
    "SOLICITUD BECA COMISION": [1, 40],  # BECA COMISIÓN, PRÓRROGA DE BECA COMISIÓN
    "LIBERACION DE SUPERVISORES": [],  # Sin motivo de movimiento
    "CAPTURA DE GRAVIDEZ": [],  # Sin motivo de movimiento
    "JUSTIFICACION DE RETROACTIVIDAD": [],  # Sin motivo de movimiento
}

_NOMBRE_MOTIVO_99 = "ALTA PROVISIONAL EN VACANTE DEFINITIVA (99)"


def ids_permitidos(nombre_plantilla):
    """Devuelve lista de ids de motivo válidos, [] si no lleva, None si se desconoce.

    Primero consulta la configuración guardada en la plantilla (diseñador).
    Si la plantilla no tiene configuración, usa el mapa histórico para no
    cambiar el comportamiento de los trámites que ya existían.
    """
    if not nombre_plantilla:
        return None
    opcion = nombre_plantilla.strip().upper()
    if opcion == _NOMBRE_MOTIVO_99:
        # Un solo motivo, forzado por el backend y oculto en el formulario.
        from .models import MotivoTramite
        return list(MotivoTramite.objects.filter(
            motivo_tramite=_NOMBRE_MOTIVO_99
        ).values_list('id', flat=True))

    # Configuración del diseñador (incluye las plantillas migradas del sistema).
    try:
        from .models import PlantillaTramite
        plantilla = PlantillaTramite.objects.filter(
            nombre__iexact=nombre_plantilla.strip()
        ).first()
        if plantilla and isinstance(plantilla.configuracion, dict) \
                and 'motivos' in plantilla.configuracion:
            motivos = plantilla.configuracion.get('motivos')
            if motivos is None:
                return None
            return [int(m) for m in motivos if str(m).isdigit()]
    except Exception:
        # Si todavía no existe la tabla/columna, seguimos con el mapa histórico.
        pass

    if opcion in MOTIVOS_POR_PLANTILLA:
        return list(MOTIVOS_POR_PLANTILLA[opcion])
    return None
