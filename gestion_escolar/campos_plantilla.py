"""Catálogo central de campos para las plantillas de trámites y oficios.

Aquí vive la única fuente de verdad de:
- Qué campos se pueden pedir en el formulario.
- A qué sección pertenece cada campo.
- Qué variables de Word alimenta cada campo.
- La configuración con la que deben seguir funcionando las plantillas que
  ya existían antes del diseñador (plantillas del sistema, no editables).

Las plantillas nuevas guardan su propia configuración en
``PlantillaTramite.configuracion``. Las del sistema se migran desde
``CONFIG_POR_PLANTILLA`` y quedan bloqueadas para edición.
"""

import re

from unidecode import unidecode

from .motivos_plantilla import MOTIVOS_POR_PLANTILLA
# ---------------------------------------------------------------------------
# Secciones del formulario
# ---------------------------------------------------------------------------

SECCIONES = {
    'titular': {
        'titulo': 'Datos del Maestro Titular',
        'orden': 10,
    },
    'interino': {
        'titulo': 'Datos del Maestro Interino',
        'orden': 20,
    },
    'adscripcion': {
        'titulo': 'Datos del Cambio de Adscripción',
        'orden': 30,
    },
    'otros': {
        'titulo': 'Otros Datos del Trámite',
        'orden': 40,
    },
    'retroactividad': {
        'titulo': 'Justificación de la Retroactividad',
        'orden': 50,
    },
    'personalizados': {
        'titulo': 'Datos Adicionales',
        'orden': 60,
    },
}

# Mapa sección -> selector que ya usa el JavaScript de generar_tramite.html.
SECCION_A_SELECTOR = {
    'titular': '#datos-titular-section',
    'interino': '#datos-interino-section',
    'adscripcion': '#cambio-adscripcion-section',
    'otros': '#otros-datos-section',
    'retroactividad': '#retroactividad-section',
    'personalizados': '#campos-personales-section',
}


# ---------------------------------------------------------------------------
# Catálogo de campos
# ---------------------------------------------------------------------------
# ``form_field`` es el nombre real dentro de TramiteForm. Algunos campos del
# formulario son de solo lectura (los displays del maestro): no se marcan como
# obligatorios porque se llenan solos al elegir al maestro.

CATALOGO_CAMPOS = {
    'maestro_titular': {
        'label': 'Maestro titular',
        'seccion': 'titular',
        'form_field': 'maestro_titular',
        'tipo': 'maestro',
        'descripcion': 'Buscador del maestro titular. Al elegirlo se llenan sus datos, '
                       'escuela, categoría, función, CURP, RFC y clave presupuestal.',
        'variables': [
            'Nombre_Titular', 'CURP_Titular', 'RFC_Titular', 'Categoria_Titular',
            'Presupuestal_Titular', 'Techo_Financiero', 'Funcion_Titular',
            'Codigo_Titular', 'Clave_CT', 'Nombre_CT', 'Turno', 'Domicilio_CT',
            'Z_Escolar', 'Sostenimiento', 'Director', 'Supervisor',
            'Nombre', 'Paterno', 'Materno',
        ],
        'obligatorio_sugerido': True,
    },
    'fecha_efecto1': {
        'label': 'Fecha inicial del titular',
        'seccion': 'titular',
        'form_field': 'fecha_efecto1',
        'tipo': 'fecha',
        'descripcion': 'Fecha de inicio de los efectos del titular.',
        'variables': ['Efecto_1', 'Efecto_1_Letra', 'I_Dia', 'I_Mes', 'I_Ano'],
    },
    'fecha_efecto2': {
        'label': 'Fecha final del titular',
        'seccion': 'titular',
        'form_field': 'fecha_efecto2',
        'tipo': 'fecha',
        'descripcion': 'Fecha de fin de los efectos del titular. Puede dejarse vacía si no tiene fin.',
        'variables': ['Efecto_2', 'F_Dia', 'F_Mes', 'F_Ano'],
    },
    'form_academica_titular': {
        'label': 'Formación académica del titular',
        'seccion': 'titular',
        'form_field': 'form_academica_titular_display',
        'tipo': 'texto',
        'solo_lectura': True,
        'descripcion': 'Se llena automáticamente con la formación académica del maestro.',
        'variables': ['Formacion_Titular'],
    },
    'ze_techo_f': {
        'label': 'Zona económica (techo financiero)',
        'seccion': 'titular',
        'form_field': 'ze_techo_f_display',
        'tipo': 'texto',
        'solo_lectura': True,
        'descripcion': 'Se llena automáticamente con la zona económica del centro de trabajo de pago.',
        'variables': ['Z_economica_Techo_F'],
    },
    'maestro_interino': {
        'label': 'Maestro interino',
        'seccion': 'interino',
        'form_field': 'maestro_interino',
        'tipo': 'maestro',
        'descripcion': 'Buscador del maestro interino. Al elegirlo se llenan sus datos y su prelación.',
        'variables': [
            'Nombre_Interino', 'CURP_Interino', 'RFC_Interino', 'Presupuestal_Interino',
            'Funcion_Interino', 'Codigo_Interino', 'Tipo_Movimiento_Interino',
            'Resultado_Alta', 'Horario', 'Horas', 'No_Prel', 'Folio_Prel', 'Tipo_Val',
            'Paterno', 'Materno', 'Nombre', 'Presupuestal_Interino_Propio',
            'Techo_Financiero_Interino', 'Nombre_Interino_Retro',
        ],
    },
    'fecha_efecto3': {
        'label': 'Fecha inicial del interino',
        'seccion': 'interino',
        'form_field': 'fecha_efecto3',
        'tipo': 'fecha',
        'descripcion': 'Fecha de inicio del interinato.',
        'variables': ['Efecto_3', 'I_Dia', 'I_Mes', 'I_Ano'],
    },
    'fecha_efecto4': {
        'label': 'Fecha final del interino',
        'seccion': 'interino',
        'form_field': 'fecha_efecto4',
        'tipo': 'fecha',
        'descripcion': 'Fecha de fin del interinato.',
        'variables': ['Efecto_4', 'F_Dia', 'F_Mes', 'F_Ano'],
    },
    'tipo_cambio': {
        'label': 'Tipo de cambio (sustitución / incremento)',
        'seccion': 'adscripcion',
        'form_field': 'tipo_cambio',
        'tipo': 'opciones',
        'opciones': [
            {'valor': 'sustitucion', 'texto': 'Sustitución'},
            {'valor': 'incremento', 'texto': 'Incremento'},
        ],
        'descripcion': 'Define si el cambio de adscripción es por sustitución o por incremento.',
        'variables': ['Sustituida'],
    },
    'maestro_sustituido': {
        'label': 'Maestro sustituido',
        'seccion': 'adscripcion',
        'form_field': 'maestro_sustituido',
        'tipo': 'maestro',
        'descripcion': 'Solo para cambios de adscripción por sustitución.',
        'variables': ['Sustituida'],
    },
    'escuela_destino': {
        'label': 'Centro de trabajo destino',
        'seccion': 'adscripcion',
        'form_field': 'escuela_destino',
        'tipo': 'escuela',
        'descripcion': 'Solo para cambios de adscripción por incremento.',
        'variables': ['Clave_CT', 'Nombre_CT', 'Turno', 'Domicilio_CT', 'Z_Escolar', 'Director', 'Supervisor'],
    },
    'folio': {
        'label': 'Folio del oficio',
        'seccion': 'otros',
        'form_field': 'folio',
        'tipo': 'texto',
        'descripcion': 'Folio manual del control de oficios.',
        'variables': ['F_OfPres'],
    },
    'observaciones': {
        'label': 'Observaciones',
        'seccion': 'otros',
        'form_field': 'observaciones',
        'tipo': 'texto_largo',
        'descripcion': 'Texto libre que se inserta en el documento.',
        'variables': ['COMENTARIOS', 'Observaciones'],
    },
    'quincena_inicial': {
        'label': 'Quincena inicial (YYYYQQ)',
        'seccion': 'otros',
        'form_field': 'quincena_inicial',
        'tipo': 'texto',
        'descripcion': 'Quincena de inicio con formato YYYYQQ (ej. 202501).',
        'variables': ['QuincenaInicio', 'QuincenaInicial'],
    },
    'quincena_final': {
        'label': 'Quincena final (YYYYQQ)',
        'seccion': 'otros',
        'form_field': 'quincena_final',
        'tipo': 'texto',
        'descripcion': 'Quincena final con formato YYYYQQ (ej. 202524).',
        'variables': ['QuincenaFinal'],
    },
    'fecha_al_corte': {
        'label': 'Fecha al corte',
        'seccion': 'otros',
        'form_field': 'fecha_al_corte',
        'tipo': 'fecha',
        'descripcion': 'Fecha de corte para el cálculo de antigüedad.',
        'variables': ['fecha_al_corte'],
    },
    'fecha_del_calculo': {
        'label': 'Fecha del cálculo',
        'seccion': 'otros',
        'form_field': 'fecha_del_calculo',
        'tipo': 'fecha',
        'descripcion': 'Fecha base para el cálculo de antigüedad.',
        'variables': ['F_Calculo'],
    },
    'antiguedad_funcion': {
        'label': 'Antigüedad en la función',
        'seccion': 'otros',
        'form_field': 'antiguedad_funcion',
        'tipo': 'texto',
        'descripcion': 'Se puede calcular automáticamente con las dos fechas anteriores.',
        'variables': ['antiguedad_funcion'],
    },
    'antiguedad_categoria': {
        'label': 'Antigüedad en la categoría',
        'seccion': 'otros',
        'form_field': 'antiguedad_categoria',
        'tipo': 'texto',
        'descripcion': 'Se puede calcular automáticamente con las dos fechas anteriores.',
        'variables': ['antiguedad_categoria'],
    },
    'fecha_del_calculo_servicio': {
        'label': 'Fecha de ingreso al servicio',
        'seccion': 'otros',
        'form_field': 'fecha_del_calculo_servicio',
        'tipo': 'fecha',
        'descripcion': 'Fecha de ingreso al servicio para el cálculo de antigüedad.',
        'variables': [],
    },
    'antiguedad_servicio': {
        'label': 'Antigüedad en el servicio',
        'seccion': 'otros',
        'form_field': 'antiguedad_servicio',
        'tipo': 'texto',
        'descripcion': 'Antigüedad en el servicio.',
        'variables': ['antiguedad_servicio'],
    },
    'fecha_adscripcion': {
        'label': 'Fecha de adscripción',
        'seccion': 'otros',
        'form_field': 'fecha_adscripcion',
        'tipo': 'fecha',
        'descripcion': 'Fecha de adscripción al centro de trabajo.',
        'variables': ['fecha_adscripcion'],
    },
    'incentivos': {
        'label': 'Incentivos',
        'seccion': 'otros',
        'form_field': 'incentivos',
        'tipo': 'texto',
        'descripcion': 'Incentivos del maestro. Se llena automáticamente y se puede ajustar.',
        'variables': ['incentivos'],
    },
    'opcionjustificacion': {
        'label': 'Opción de justificación',
        'seccion': 'retroactividad',
        'form_field': 'opcionjustificacion',
        'tipo': 'opciones',
        'descripcion': 'Motivo por el que se justifica la retroactividad.',
        'variables': ['opcionjustificacion', 'Razon_Retroactividad'],
    },
    'fecha_usicamm': {
        'label': 'Fecha de asignación USICAMM',
        'seccion': 'retroactividad',
        'form_field': 'fecha_usicamm',
        'tipo': 'fecha',
        'descripcion': 'Solo se usa cuando la justificación es USICAMM.',
        'variables': ['Fecha_USICAMM', 'Fecha_USICAMM_Letra'],
    },
    'texto_razon_otro': {
        'label': 'Especifique la razón',
        'seccion': 'retroactividad',
        'form_field': 'texto_razon_otro',
        'tipo': 'texto_largo',
        'descripcion': 'Solo se usa cuando la justificación es "Otro".',
        'variables': ['Razon_Retroactividad'],
    },
    'archivo_plantilla_especifico': {
        'label': 'Variante de plantilla (.docx)',
        'seccion': None,
        'form_field': 'archivo_plantilla_especifico',
        'tipo': 'variante',
        'descripcion': 'Permite elegir entre las variantes Art. 3 y Art. 36 de la solicitud de asignación.',
        'variables': [],
        'obligatorio_sugerido': False,
    },
}

# Campos que el formulario siempre debe mostrar para poder operar.
CAMPOS_BASE = {'plantilla', 'motivo_tramite'}

# Campos de solo lectura: nunca se marcan obligatorios en el servidor.
CAMPOS_SOLO_LECTURA = {
    clave for clave, info in CATALOGO_CAMPOS.items()
    if info.get('solo_lectura')
}


def campo_a_form_field(campo):
    """Devuelve el nombre real del campo de TramiteForm."""
    info = CATALOGO_CAMPOS.get(campo)
    if info:
        return info.get('form_field', campo)
    return campo


# ---------------------------------------------------------------------------
# Configuración de las plantillas que ya existían (base del sistema)
# ---------------------------------------------------------------------------
# Los campos son exactamente los que hoy muestra el JavaScript. No se agregan
# ni se quitan para que los 23 trámites sigan funcionando igual.

_SIN_MOTIVO_SISTEMA = {
    'CAPTURA DE GRAVIDEZ',
    'CAMBIO DE EFECTOS',
    'CONSTANCIA DE HORIZONTAL',
    'PRESENTACION LABORAL PARA CAMBIO DE ADSCRIPCION',
    'LIBERACION DE SUPERVISORES',
    'SOLICITUD BECA COMISION',
    'ALTA PROVISIONAL EN VACANTE DEFINITIVA (99)',
    'JUSTIFICACION DE RETROACTIVIDAD',
}

_CAMPOS_POR_PLANTILLA = {
    'REINGRESO': ['maestro_titular', 'fecha_efecto1', 'fecha_efecto2', 'maestro_interino',
                  'fecha_efecto3', 'fecha_efecto4', 'folio', 'observaciones'],
    'FILIACION': ['maestro_titular', 'fecha_efecto1', 'fecha_efecto2', 'maestro_interino',
                  'fecha_efecto3', 'fecha_efecto4', 'folio', 'observaciones'],
    'REINGRESO SIN PRELACION': ['maestro_titular', 'fecha_efecto1', 'fecha_efecto2',
                                'maestro_interino', 'fecha_efecto3', 'fecha_efecto4',
                                'folio', 'observaciones'],
    'SOLICITUD DE ASIGNACION': ['maestro_titular', 'maestro_interino', 'fecha_efecto3',
                                'fecha_efecto4', 'folio', 'observaciones',
                                'archivo_plantilla_especifico'],
    # Variante Art. 36 de la solicitud de asignación. Se elige desde el campo
    # "archivo_plantilla_especifico" de la plantilla base, no desde el listado,
    # pero se conserva como plantilla del sistema (solo lectura).
    'SOLICITUD DE ASIGNACION 36': ['maestro_titular', 'maestro_interino', 'fecha_efecto3',
                                   'fecha_efecto4', 'folio', 'observaciones',
                                   'archivo_plantilla_especifico'],
    'JUSTIFICACION DE PERFIL': ['maestro_titular', 'fecha_efecto1', 'fecha_efecto2',
                                'maestro_interino', 'fecha_efecto3', 'fecha_efecto4',
                                'folio', 'observaciones'],
    'CONSTANCIAS': ['maestro_titular', 'motivo_tramite', 'folio', 'quincena_inicial',
                    'quincena_final'],
    'OFICIO DE REINCORPORACION': ['maestro_titular', 'folio', 'fecha_efecto1'],
    'CAMBIO DEL CENTRO DE TRABAJO': ['maestro_titular'],
    'CUADRO CAMBIOS CON FOLIO': ['maestro_titular', 'folio', 'fecha_efecto1'],
    'PROPUESTA DE MOVIMIENTO': ['maestro_titular', 'folio', 'fecha_efecto1'],
    'ALTA INICIAL (09)': ['maestro_titular', 'no_prel_display', 'folio_prel_display',
                          'tipo_val_display', 'fecha_efecto1', 'fecha_efecto2', 'folio',
                          'observaciones'],
    'ALTA PROVISIONAL EN VACANTE DEFINITIVA (99)': [
        'maestro_titular', 'maestro_interino', 'no_prel_display', 'folio_prel_display',
        'tipo_val_display', 'fecha_efecto3', 'fecha_efecto4', 'folio', 'observaciones',
    ],
    'REPORTE DE VACANCIA': ['maestro_titular', 'fecha_efecto1', 'fecha_efecto2',
                            'maestro_interino'],
    'CONSTANCIA DE CAMBIO': ['maestro_titular', 'motivo_tramite', 'folio', 'fecha_al_corte',
                             'fecha_del_calculo', 'antiguedad_funcion', 'antiguedad_categoria',
                             'fecha_adscripcion', 'incentivos'],
    'CONSTANCIA DE HORIZONTAL': ['maestro_titular', 'motivo_tramite', 'folio', 'fecha_al_corte',
                                 'fecha_del_calculo', 'antiguedad_funcion', 'incentivos'],
    'CONSTANCIA DE RECATEGORIZACIÓN': ['maestro_titular', 'motivo_tramite', 'folio',
                                       'fecha_al_corte', 'fecha_del_calculo',
                                       'antiguedad_funcion', 'incentivos',
                                       'form_academica_titular', 'ze_techo_f'],
    'PRESENTACION LABORAL': ['maestro_titular', 'maestro_interino', 'fecha_efecto3',
                             'fecha_efecto4', 'folio', 'observaciones'],
    'PRESENTACION LABORAL PARA CAMBIO DE ADSCRIPCION': [
        'maestro_titular', 'tipo_cambio', 'maestro_sustituido', 'escuela_destino',
        'fecha_efecto1', 'fecha_efecto3', 'fecha_efecto4', 'folio', 'observaciones',
    ],
    'CAPTURA DE GRAVIDEZ': ['maestro_titular', 'fecha_efecto1', 'fecha_efecto2'],
    'CAMBIO DE EFECTOS': ['maestro_titular', 'maestro_interino', 'fecha_efecto3',
                          'fecha_efecto4', 'folio', 'observaciones'],
    'LIBERACION DE SUPERVISORES': ['maestro_titular', 'folio', 'fecha_efecto1',
                                   'observaciones'],
    'SOLICITUD BECA COMISION': ['maestro_titular', 'folio', 'fecha_al_corte',
                                'fecha_del_calculo', 'antiguedad_funcion'],
    'JUSTIFICACION DE RETROACTIVIDAD': ['maestro_interino', 'folio', 'opcionjustificacion',
                                        'fecha_usicamm', 'texto_razon_otro'],
}

_REQUERIDOS_ESPECIALES = {
    'JUSTIFICACION DE RETROACTIVIDAD': ['maestro_interino', 'opcionjustificacion'],
}

_MOTIVO_AUTO = {
    'ALTA INICIAL (09)': 39,
    'CONSTANCIA DE RECATEGORIZACIÓN': 17,
    'SOLICITUD BECA COMISION': 1,
}

_CALCULA_ANTIGUEDAD = {
    'CONSTANCIA DE CAMBIO',
    'CONSTANCIA DE HORIZONTAL',
    'CONSTANCIA DE RECATEGORIZACIÓN',
    'SOLICITUD BECA COMISION',
}

# Plantillas del sistema que usan una variante especial cuando el maestro está
# desubicado. Se conserva el comportamiento actual.
_PLANTILLAS_DESUBICADO = {'REINGRESO', 'FILIACION'}


def normalizar_nombre(nombre):
    """Mayúsculas y sin acentos, para comparar nombres escritos por el usuario."""
    return unidecode((nombre or '')).upper().strip()


_CONFIG_POR_NOMBRE_NORMALIZADO = {
    normalizar_nombre(nombre): nombre for nombre in _CAMPOS_POR_PLANTILLA
}


def config_sistema(nombre):
    """Configuración con la que una plantilla del sistema debe seguir operando.

    Devuelve ``None`` si el nombre no pertenece a las plantillas conocidas.
    """
    clave = normalizar_nombre(nombre)
    nombre = _CONFIG_POR_NOMBRE_NORMALIZADO.get(clave)
    if nombre is None:
        return None
    campos = _CAMPOS_POR_PLANTILLA.get(nombre)
    if campos is None:
        return None

    if nombre in _REQUERIDOS_ESPECIALES:
        requeridos = list(_REQUERIDOS_ESPECIALES[nombre])
    else:
        requeridos = ['maestro_titular'] if 'maestro_titular' in campos else []

    motivos = MOTIVOS_POR_PLANTILLA.get(nombre)
    return {
        'version': 1,
        'origen': 'sistema',
        'campos': list(campos),
        'requeridos': requeridos,
        'motivos': list(motivos) if motivos is not None else None,
        'mostrar_motivo': nombre not in _SIN_MOTIVO_SISTEMA,
        'motivo_auto': _MOTIVO_AUTO.get(nombre),
        'calcular_antiguedad': nombre in _CALCULA_ANTIGUEDAD,
        'usa_variante_desubicado': nombre in _PLANTILLAS_DESUBICADO,
        'campos_personalizados': [],
    }


# Lista de nombres de las 23 plantillas del sistema.
PLANTILLAS_SISTEMA = sorted(_CAMPOS_POR_PLANTILLA)


def config_vacia():
    return {
        'version': 1,
        'origen': 'usuario',
        'campos': [],
        'requeridos': [],
        'motivos': [],
        'mostrar_motivo': False,
        'motivo_auto': None,
        'calcular_antiguedad': False,
        'usa_variante_desubicado': False,
        'campos_personalizados': [],
    }


def normalizar_config(config):
    """Completa una configuración guardada con las claves esperadas."""
    base = config_vacia()
    if isinstance(config, dict):
        base.update(config)
    base['campos'] = [c for c in (base.get('campos') or []) if isinstance(c, str)]
    base['requeridos'] = [c for c in (base.get('requeridos') or []) if isinstance(c, str)]
    if 'motivos' in base and base['motivos'] is not None:
        base['motivos'] = [int(m) for m in base['motivos'] if str(m).isdigit()]
    base['campos_personalizados'] = [
        c for c in (base.get('campos_personalizados') or []) if isinstance(c, dict)
    ]
    return base


def config_de_plantilla(plantilla):
    """Configuración efectiva de una PlantillaTramite (o vacía si no hay)."""
    if plantilla is None:
        return config_vacia()
    config = getattr(plantilla, 'configuracion', None)
    sistema = config_sistema(getattr(plantilla, 'nombre', ''))
    if isinstance(config, dict) and config.get('campos') is not None:
        guardada = normalizar_config(config)
        # Configuraciones guardadas antes de existir "motivo_auto" lo traen
        # vacío: se completa con el valor del sistema sin tocar el resto.
        if not guardada.get('motivo_auto') and sistema:
            motivo_auto = sistema.get('motivo_auto')
            motivos = guardada.get('motivos')
            if motivo_auto and (not motivos or motivo_auto in motivos):
                guardada['motivo_auto'] = motivo_auto
        return guardada
    if sistema:
        return normalizar_config(sistema)
    return config_vacia()


def secciones_usadas(campos, personalizados=None):
    """Devuelve las secciones (en orden) que usan los campos indicados."""
    usadas = set()
    for campo in campos or []:
        info = CATALOGO_CAMPOS.get(campo)
        if info and info.get('seccion'):
            usadas.add(info['seccion'])
    if personalizados:
        usadas.add('personalizados')
    return [
        clave for clave in sorted(SECCIONES, key=lambda k: SECCIONES[k]['orden'])
        if clave in usadas
    ]


def config_para_js(plantilla):
    """Configuración compacta que consume generar_tramite.html."""
    config = config_de_plantilla(plantilla)
    campos = list(config.get('campos') or [])
    personalizados = config.get('campos_personalizados') or []
    for custom in personalizados:
        nombre_campo = nombre_campo_personalizado(
            getattr(plantilla, 'id', 0), custom.get('variable', ''))
        if nombre_campo:
            campos.append(nombre_campo)
    secciones = [
        SECCION_A_SELECTOR[s] for s in secciones_usadas(config.get('campos'), personalizados)
        if s in SECCION_A_SELECTOR
    ]
    return {
        'campos': campos,
        'secciones': secciones,
        'mostrar_motivo': bool(config.get('mostrar_motivo')),
        'motivo_auto': config.get('motivo_auto') or '',
        'calcular_antiguedad': bool(config.get('calcular_antiguedad')),
    }


def configuraciones_para_js(queryset):
    """Mapa nombre_en_mayusculas -> config_para_js para todos los registros."""
    resultado = {}
    for plantilla in queryset:
        resultado[(plantilla.nombre or '').strip().upper()] = config_para_js(plantilla)
    return resultado


def plantillas_sin_motivo_js(queryset):
    return [
        (p.nombre or '').strip().upper()
        for p in queryset
        if not config_para_js(p)['mostrar_motivo']
    ]


# ---------------------------------------------------------------------------
# Campos personalizados
# ---------------------------------------------------------------------------

TIPOS_CAMPO_PERSONALIZADO = {
    'texto': 'Texto',
    'texto_largo': 'Texto largo',
    'fecha': 'Fecha',
    'numero': 'Número',
    'opciones': 'Lista de opciones',
}


def nombre_campo_personalizado(plantilla_id, variable):
    """Nombre interno del campo en TramiteForm (evita choques entre plantillas)."""
    variable = (variable or '').strip()
    if not variable or not plantilla_id:
        return ''
    variable_segura = re.sub(r'\W', '_', variable, flags=re.UNICODE).strip('_')
    if not variable_segura:
        return ''
    if variable_segura[0].isdigit():
        variable_segura = f'v_{variable_segura}'
    return f'custom_{plantilla_id}_{variable_segura}'


def variables_disponibles():
    """Catálogo plano de variables de Word, para la guía del diseñador."""
    filas = []
    vistos = set()
    for campo, info in CATALOGO_CAMPOS.items():
        for variable in info.get('variables') or []:
            if variable in vistos:
                continue
            vistos.add(variable)
            filas.append({
                'variable': variable,
                'campo': campo,
                'descripcion': info.get('label') or campo,
            })
    return sorted(filas, key=lambda fila: fila['variable'].lower())


def campos_por_seccion():
    """Agrupa el catálogo por sección para pintar el diseñador."""
    grupos = {}
    for campo, info in CATALOGO_CAMPOS.items():
        clave = info.get('seccion')
        if not clave:
            continue
        grupos.setdefault(clave, []).append({
            'clave': campo,
            'label': info.get('label') or campo,
            'descripcion': info.get('descripcion') or '',
            'tipo': info.get('tipo') or 'texto',
            'obligatorio_sugerido': bool(info.get('obligatorio_sugerido')),
            'variables': info.get('variables') or [],
        })
    return [
        {
            'clave': clave,
            'titulo': SECCIONES[clave]['titulo'],
            'campos': grupos.get(clave, []),
        }
        for clave in sorted(SECCIONES, key=lambda k: SECCIONES[k]['orden'])
        if grupos.get(clave)
    ]
