import os
import openpyxl
from docxtpl import DocxTemplate
from datetime import datetime, date, timedelta
from django.conf import settings
import gspread
from google.oauth2 import service_account

# Asegúrate de que los modelos necesarios estén disponibles.
# A veces es mejor pasar los objetos como argumentos en lugar de importarlos directamente
# para evitar dependencias circulares, pero por ahora los importamos.
from ..models import Maestro, Escuela

# Carpeta canónica única de plantillas: todo el sistema debe jalar de aquí.
# Word: gestion_escolar/templates/tramites/Plantillas/Word
# Excel: gestion_escolar/templates/tramites/Plantillas/Excel
PLANTILLAS_WORD_DIR = os.path.join(
    settings.BASE_DIR, 'gestion_escolar', 'templates', 'tramites', 'Plantillas', 'Word')
PLANTILLAS_EXCEL_DIR = os.path.join(
    settings.BASE_DIR, 'gestion_escolar', 'templates', 'tramites', 'Plantillas', 'Excel')
# Respaldo temporal: antigua carpeta raíz (no agregar plantillas nuevas aquí).
PLANTILLAS_WORD_DIR_LEGACY = os.path.join(
    settings.BASE_DIR, 'tramites', 'Plantillas', 'Word')
PLANTILLAS_EXCEL_DIR_LEGACY = os.path.join(
    settings.BASE_DIR, 'tramites', 'Plantillas', 'Excel')


def resolver_ruta_plantilla(ruta):
    """Resuelve la ruta de una plantilla a un archivo existente.

    Acepta rutas absolutas viejas (C:\\...) o relativas y siempre prefiere
    la carpeta canónica. Si el archivo ya no está donde dice el registro,
    lo busca por nombre en Word/Excel canónicos y luego en los legacy.
    Devuelve la ruta absoluta o None si no existe.
    """
    if not ruta:
        return None
    ruta_str = str(ruta)
    # 1) Tal cual (absoluta existente o relativa existente desde BASE_DIR)
    if os.path.isabs(ruta_str) and os.path.exists(ruta_str):
        return ruta_str
    candidato = ruta_str if os.path.isabs(ruta_str) else os.path.join(str(settings.BASE_DIR), ruta_str)
    if os.path.exists(candidato):
        return candidato
    # 2) Por nombre en carpetas canónicas y luego legacy
    nombre = os.path.basename(ruta_str)
    for carpeta in (PLANTILLAS_WORD_DIR, PLANTILLAS_EXCEL_DIR,
                    PLANTILLAS_WORD_DIR_LEGACY, PLANTILLAS_EXCEL_DIR_LEGACY):
        intento = os.path.join(carpeta, nombre)
        if os.path.exists(intento):
            return intento
    return None

# Helper function to get full name
def get_full_name(maestro):
    if not maestro: return ""
    return f"{maestro.nombres or ''} {maestro.a_paterno or ''} {maestro.a_materno or ''}".strip()

# Helper function to get school info
def get_school_info(escuela):
    if not escuela: return {'nombre_ct': '', 'id_escuela': '', 'turno': '', 'domicilio': '', 'zona_economica': '', 'zona_esc_numero': '', 'region': '', 'u_d': '', 'sostenimiento': ''}
    return {
        'nombre_ct': escuela.nombre_ct or '',
        'id_escuela': escuela.id_escuela or '',
        'turno': escuela.get_turno_display() or '',
        'domicilio': escuela.domicilio or '',
        'zona_economica': escuela.zona_economica or '',
        'zona_esc_numero': escuela.zona_esc.numero if escuela.zona_esc else '',
        'region': escuela.region or '',
        'u_d': escuela.u_d or '',
        'sostenimiento': escuela.get_sostenimiento_display() or '',
    }

# Regex tolerante: coincide con DIRECTOR(A), DIRECTOR (A), DIRECTOR, etc.
import re

def es_status_activo(status):
    """Devuelve True si el valor de status representa a un maestro activo,
    tolerando variantes de mayúsculas y espacios (ej. 'ACTIVO', 'ACTIVA', 'ACTIVO ')."""
    return (status or '').strip().upper().startswith('ACTIV')


def contar_personal(queryset=None):
    """Cuenta PERSONAS únicas (por CURP), no registros/plazas.

    Recibe un queryset de Maestro (o None para todos). Devuelve un dict:
      {'personas': n_personas_unicas, 'plazas': n_registros}
    Una persona con varias plazas (mismo CURP) cuenta como UNA. Las plazas sin CURP
    se consideran personas individuales (cada registro cuenta como una persona).
    """
    from django.db.models import Q
    qs = queryset if queryset is not None else Maestro.objects.all()
    plazas = qs.count()
    # Agrupar por CURP no vacía: cada CURP distinta = 1 persona
    con_curp = qs.exclude(curp__isnull=True).exclude(curp='')
    personas_con_curp = con_curp.values('curp').distinct().count()
    # Registros sin CURP -> cada uno cuenta como persona propia
    sin_curp = qs.filter(Q(curp__isnull=True) | Q(curp='')).count()
    personas = personas_con_curp + sin_curp
    return {'personas': personas, 'plazas': plazas}


# Mapa único de funciones canónicas -> valores de Maestro.funcion.
# Centralizado aquí para que personal.py (lista_por_funcion) y reportes.py
# (exportar_maestros_excel) usen la misma definición y no se desincronicen.
FUNCION_MAPPING = {
    'DIRECTOR': {'display': 'Director', 'values': ['DIRECTOR(A)']},
    'SUPERVISOR': {'display': 'Supervisor', 'values': ['SUPERVISOR(A)']},
    'MAESTRO_GRUPO': {'display': 'Maestro de Grupo', 'values': ['MAESTRO(A) DE GRUPO', 'MAESTRO(A) DE GRUPO CON ESPECIALIDAD', 'MAESTRO(A) DE GRUPO ESPECIALISTA']},
    'DOCENTE_APOYO': {'display': 'Docente de Apoyo', 'values': ['MAESTRO(A) ESPECIALISTA DOCENTE DE APOYO']},
    'PSICOLOGO': {'display': 'Psicólogo', 'values': ['PSICÓLOGO(A)']},
    'TRABAJADOR_SOCIAL': {'display': 'Trabajador Social', 'values': ['TRABAJADOR(A) SOCIAL']},
    'NIÑERO': {'display': 'Niñero', 'values': ['NIÑERO(A)']},
    'SECRETARIO': {'display': 'Secretario', 'values': ['SECRETARIO(A)']},
    'INTENDENTE': {'display': 'Intendente', 'values': ['INTENDENTE']},
    'VELADOR': {'display': 'Velador', 'values': ['VELADOR']},
    'VIGILANTE': {'display': 'Vigilante', 'values': ['VIGILANTE']},
    'OTRO': {'display': 'Otro', 'values': ['OTRO']},
    'APOYO_TECNICO_PEDAGOGICO': {'display': 'Apoyo Técnico Pedagógico', 'values': ['APOYO TÉCNICO PEDAGÓGICO']},
    'MAESTRO_TALLER': {'display': 'Maestro de Taller', 'values': ['MAESTRO(A) DE TALLER']},
    'MAESTRO_MUSICA': {'display': 'Maestro de Música', 'values': ['MAESTRO(A) MÚSICA']},
    'MAESTRO_EDUCACION_FISICA': {'display': 'Maestro de Educación Física', 'values': ['MAESTRO(A) DE EDUCACIÓN FÍSICA']},
    'MAESTRO_EDUCACION_ARTISTICA': {'display': 'Maestro de Educación Artística', 'values': ['MAESTRO(A) DE EDUCACIÓN ARTÍSTICA']},
    'MEDICO': {'display': 'Médico', 'values': ['MÉDICO(A)']},
    'PROMOTOR_TIC': {'display': 'Promotor TIC', 'values': ['PROMOTOR TIC']},
    'TERAPISTA_FISICO': {'display': 'Terapista Físico', 'values': ['TERAPISTA FÍSICO']},
    'BIBLIOTECARIO': {'display': 'Bibliotecario', 'values': ['BIBLIOTECARIO']},
    'ADMINISTRATIVO_ESPECIALIZADO': {'display': 'Administrativo Especializado', 'values': ['ADMINISTRATIVO ESPECIALIZADO']},
    'OFICIAL_SERVICIOS_MANTENIMIENTO': {'display': 'Oficial de Servicios y Mantenimiento', 'values': ['OFICIAL DE SERVICIOS Y MANTENIMIENTO']},
    'ASISTENTE_DE_SERVICIOS': {'display': 'Asistente de Servicios', 'values': ['ASISTENTE DE SERVICIOS']},
    'ASESOR_JURIDICO': {'display': 'Asesor Jurídico', 'values': ['ASESOR JURÍDICO']},
    'AUXILIAR_DE_GRUPO': {'display': 'Auxiliar de Grupo', 'values': ['AUXILIAR DE GRUPO']},
    'MAESTRO_COMUNICACION': {'display': 'Maestro de Comunicación', 'values': ['MAESTRO(A) DE COMUNICACIÓN']},
    'MAESTRO_AULA_HOSPITALARIA': {'display': 'Maestro Aula Hospitalaria', 'values': ['MAESTRO(A) AULA HOSPITALARIA']},
    'NO_ESPECIFICADO': {'display': 'No Especificado', 'values': ['NO ESPECIFICADO']},
}

# Helper function to get director
def elegir_director_activo(escuela):
    """Elige al director de un centro de trabajo con lógica priorizada:
    1) Maestro con función DIRECTOR y status ACTIVO y categoría E0629 (director formal).
    2) Maestro con función DIRECTOR y status ACTIVO (responsable de dirección sin categoría).
    Se excluye siempre a los INACTIVO. Devuelve el maestro o None.
    """
    if not escuela:
        return None
    candidatos = Maestro.objects.filter(
        id_escuela=escuela,
        funcion__in=['DIRECTOR(A)'],
    )
    activos = [m for m in candidatos if es_status_activo(m.status)]
    if not activos:
        return None
    # Preferir categoría E0629 (director de educación especial)
    for m in activos:
        if m.categog and m.categog.id_categoria == 'E0629':
            return m
    return activos[0]

def get_director_info(escuela):
    if not escuela:
        return {'nombre': 'DIRECTOR NO ENCONTRADO', 'nivel': ''}
    director = elegir_director_activo(escuela)
    if director:
        return {'nombre': get_full_name(director), 'nivel': director.nivel_estudio or ''}
    return {'nombre': 'DIRECTOR NO ENCONTRADO', 'nivel': ''}

# Helper function to get supervisor
def get_supervisor_info(zona):
    if not zona: return {'nombre': 'SUPERVISOR NO ENCONTRADO', 'nivel': ''}
    supervisor = Maestro.objects.filter(id_escuela__zona_esc=zona, funcion__in=['SUPERVISOR(A)']).first()
    if supervisor:
        return {'nombre': get_full_name(supervisor), 'nivel': supervisor.nivel_estudio or ''}
    return {'nombre': 'SUPERVISOR NO ENCONTRADO', 'nivel': ''}

# Helper function to get user initials
def get_user_initials(user):
    if not user:
        return ""
    
    full_name = user.get_full_name()
    
    if not full_name:
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    if not full_name:
        return user.username[0].lower() if user.username else ''

    parts = full_name.split()
    initials = "".join([part[0] for part in parts if part])
    return initials.lower()

def get_month_diff(d1, d2):
    if d1 > d2:
        d1, d2 = d2, d1
    months = (d2.year - d1.year) * 12 + d2.month - d1.month
    if d2.day < d1.day:
        months -= 1
    return months

def numero_a_letras_general(num):
    unidades = ["", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
    dieces = ["", "diez", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
    centenas = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"]
    especiales = {
        11: "once", 12: "doce", 13: "trece", 14: "catorce", 15: "quince",
        16: "dieciséis", 17: "diecisiete", 18: "dieciocho", 19: "diecinueve",
        21: "veintiuno", 22: "veintidós", 23: "veintitrés", 24: "veinticuatro",
        25: "veinticinco", 26: "veintiséis", 27: "veintisiete", 28: "veintiocho", 29: "veintinueve"
    }

    if num == 0: return "cero"
    if num in especiales: return especiales[num]

    if num < 10: return unidades[num]
    if num < 30:
        if num % 10 == 0: return dieces[num // 10]
        return dieces[num // 10] + " y " + unidades[num % 10]
    if num < 100:
        if num % 10 == 0: return dieces[num // 10]
        return dieces[num // 10] + " y " + unidades[num % 10]
    if num == 100: return "cien"
    if num < 1000:
        if num % 100 == 0: return centenas[num // 100]
        return centenas[num // 100] + " " + numero_a_letras_general(num % 100)
    if num == 1000: return "mil"
    if num < 2000:
        return "mil " + numero_a_letras_general(num - 1000)
    if num < 1000000:
        miles = num // 1000
        resto = num % 1000
        if miles == 1:
            letras = "mil"
        else:
            letras = numero_a_letras_general(miles) + " mil"
        if resto > 0:
            letras += " " + numero_a_letras_general(resto)
        return letras
    return str(num)

def convertir_fecha_a_letras(fecha):
    dia = numero_a_letras_general(fecha.day)
    meses_letras = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    mes = meses_letras[fecha.month - 1]
    anio = numero_a_letras_general(fecha.year)
    return f"{dia} de {mes} del {anio}"

def format_date_for_solicitud_asignacion(fecha):
    if not fecha:
        return ''
    meses_espanol = [
        "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
        "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
    ]
    dia = fecha.day
    mes = meses_espanol[fecha.month - 1]
    anio = fecha.year
    return f"{dia:02d} DE {mes} DEL {anio}"

def serialize_form_data(cleaned_data):
    serialized_data = {}
    for key, value in cleaned_data.items():
        if hasattr(value, 'pk'):
            serialized_data[key] = value.pk
        elif isinstance(value, (date, datetime)):
            serialized_data[key] = value.isoformat()
        elif isinstance(value, dict):
            serialized_data[key] = serialize_form_data(value)
        elif isinstance(value, list):
            serialized_data[key] = [
                item.pk if hasattr(item, 'pk') else
                item.isoformat() if isinstance(item, (date, datetime)) else
                item
                for item in value
            ]
        else:
            serialized_data[key] = value
    return serialized_data

def send_to_google_sheet(row_data):
    # print("DEBUG GS: Iniciando envío a Google Sheets...") # Comentado para producción
    try:
        if not hasattr(settings, 'GOOGLE_SHEETS_CREDENTIALS'):
            return False, "Configuración de credenciales no encontrada"
        creds_json = settings.GOOGLE_SHEETS_CREDENTIALS
        if not creds_json.get('private_key') or not creds_json.get('client_email'):
            return False, "Credenciales incompletas - falta private_key o client_email"
        
        # Crear una copia de las credenciales para modificar la clave privada
        creds_for_auth = creds_json.copy()
        # Reemplazar los '\n' escapados por saltos de línea reales
        creds_for_auth['private_key'] = creds_for_auth['private_key'].replace('\\n', '\n')
        
        # print(f"DEBUG GS: Usando cuenta: {creds_for_auth['client_email']}") # Comentado para producción
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = service_account.Credentials.from_service_account_info(creds_for_auth, scopes=SCOPES)
        # Usar gspread.Client directamente con el objeto de credenciales
        gc = gspread.Client(auth=credentials)
        # print("DEBUG GS: ✅ Autenticación exitosa") # Comentado para producción
        spreadsheet = gc.open_by_key(settings.GOOGLE_SHEET_ID)
        worksheet = spreadsheet.worksheet(settings.GOOGLE_SHEET_WORKSHEET_NAME)
        # print("DEBUG GS: ✅ Hoja abierta correctamente") # Comentado para producción
        cleaned_data = []
        for item in row_data:
            if item is None:
                cleaned_data.append('')
            elif isinstance(item, (date, datetime)):
                cleaned_data.append(item.strftime('%Y-%m-%d'))
            else:
                cleaned_data.append(str(item))
        # Escribir en la primera fila realmente vacía empezando en columna A.
        # (El append_row automático de Google adivinaba mal la posición con
        # huecos en la hoja y cada envío caía más a la derecha.)
        filas = worksheet.get_all_values()
        ultima_con_datos = 0
        for i, fila in enumerate(filas, start=1):
            if any((c or '').strip() for c in fila):
                ultima_con_datos = i
        siguiente = max(ultima_con_datos + 1, 2)
        worksheet.update(values=[cleaned_data], range_name=f'A{siguiente}')
        # print(f"DEBUG GS: ✅ Fila agregada en A{siguiente}") # Comentado para producción
        return True, f"Datos enviados correctamente a Google Sheets (fila {siguiente})"
    except gspread.exceptions.SpreadsheetNotFound:
        error_msg = "Google Sheet no encontrado. Verifica el GOOGLE_SHEET_ID."
        # print(f"DEBUG GS: ❌ {error_msg}") # Comentado para producción
        return False, error_msg
    except gspread.exceptions.WorksheetNotFound:
        error_msg = f"Hoja '{settings.GOOGLE_SHEET_WORKSHEET_NAME}' no encontrada."
        # print(f"DEBUG GS: ❌ {error_msg}") # Comentado para producción
        return False, error_msg
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        # print(f"DEBUG GS: ❌ {error_msg}") # Comentado para producción
        return False, error_msg

def calculate_time_difference(date1, date2):
    """
    Calcula la diferencia entre dos fechas y la formatea como "X años Y meses Z dias".
    Las fechas deben ser objetos datetime.date.
    """
    if not isinstance(date1, date) or not isinstance(date2, date):
        return ""

    if date1 > date2:
        date1, date2 = date2, date1 # Asegurarse de que date1 sea la fecha menor

    years = date2.year - date1.year
    months = date2.month - date1.month
    days = date2.day - date1.day

    if days < 0:
        months -= 1
        # Calcular los días restantes en el mes anterior
        # Ejemplo: 2023-03-05 - 2023-02-28. days = 5 - 28 = -23.
        # El mes de febrero tiene 28 días. 28 - 23 = 5 días.
        # Es decir, la diferencia es de 5 días de marzo.
        last_day_of_prev_month = date(date2.year, date2.month, 1) - timedelta(days=1)
        days = last_day_of_prev_month.day + days + 1 # +1 para incluir el día de inicio

    if months < 0:
        years -= 1
        months += 12

    result = []
    if years > 0:
        result.append(f"{years} año{'s' if years > 1 else ''}")
    if months > 0:
        result.append(f"{months} {'meses' if months > 1 else 'mes'}")
    if days > 0:
        result.append(f"{days} día{'s' if days > 1 else ''}")
    
    if not result:
        return "0 días"

    return " ".join(result)

def generate_word_document(form_data, plantilla_tramite, user):
    try:
        maestro_titular = form_data.get('maestro_titular')
        maestro_interino = form_data.get('maestro_interino')

        template_name_upper = plantilla_tramite.nombre.upper().strip()
        template_path = resolver_ruta_plantilla(plantilla_tramite.ruta_archivo)
        if not template_path:
            return False, f"No se encontró la plantilla '{plantilla_tramite.nombre}' en la carpeta canónica. Ruta registrada: {plantilla_tramite.ruta_archivo}"
        is_desubicado = False
        if maestro_titular and maestro_titular.techo_f and maestro_titular.id_escuela:
            if maestro_titular.techo_f.strip().upper() != maestro_titular.id_escuela.id_escuela.strip().upper():
                is_desubicado = True
        plantillas_especiales = {
            "REINGRESO": "REINGRESODESUBICADO.docx",
            "FILIACION": "FILIACIONDESUBICADO.docx",
        }
        if template_name_upper in plantillas_especiales and is_desubicado:
            nueva_plantilla_nombre = plantillas_especiales[template_name_upper]
            # Obtiene el directorio de la plantilla actual (ya es una ruta absoluta)
            directorio_plantilla = os.path.dirname(template_path)
            # Construye la ruta absoluta a la plantilla especial
            template_path = os.path.join(directorio_plantilla, nueva_plantilla_nombre)
            print(f"DEBUG: Maestro desubicado detectado para {template_name_upper}. Usando plantilla especial: {template_path}")
        
        doc = DocxTemplate(template_path)
        
        motivo_tramite_obj = form_data.get('motivo_tramite')
        nombre_titular = get_full_name(maestro_titular)
        curp_titular = maestro_titular.curp or '' if maestro_titular else ''
        rfc_titular = maestro_titular.rfc or '' if maestro_titular else ''
        cat_obj = maestro_titular.categog if maestro_titular and maestro_titular.categog else None
        categoria_titular = cat_obj.descripcion if cat_obj else ''
        codigo_categoria_titular = cat_obj.id_categoria if cat_obj else ''
        presupuestal_titular = maestro_titular.clave_presupuestal or '' if maestro_titular else ''
        techo_financiero_titular = maestro_titular.techo_f or '' if maestro_titular else ''
        funcion_titular = maestro_titular.funcion or '' if maestro_titular else ''
        codigo_titular = maestro_titular.codigo if maestro_titular else ''
        # Forzar código 09 si el trámite es ALTA INICIAL (09)
        if plantilla_tramite.nombre == "ALTA INICIAL (09)":
            codigo_titular = "09"
        
        # Extraer partes del nombre del titular
        paterno_titular = maestro_titular.a_paterno or '' if maestro_titular else ''
        materno_titular = maestro_titular.a_materno or '' if maestro_titular else ''
        nombre_titular_solo = maestro_titular.nombres or '' if maestro_titular else ''
        domicilio_part_titular = maestro_titular.domicilio_part or '' if maestro_titular else ''
        codigo_postal_titular = maestro_titular.codigo_postal or '' if maestro_titular else ''
        poblacion_titular = maestro_titular.poblacion or '' if maestro_titular else ''
        telefono_titular = maestro_titular.telefono or '' if maestro_titular else ''
        


        nombre_interino = get_full_name(maestro_interino)
        curp_interino = maestro_interino.curp or '' if maestro_interino else ''
        rfc_interino = maestro_interino.rfc or '' if maestro_interino else ''
        domicilio_part_interino = maestro_interino.domicilio_part or '' if maestro_interino else ''
        codigo_postal_interino = maestro_interino.codigo_postal or '' if maestro_interino else ''
        poblacion_interino = maestro_interino.poblacion or '' if maestro_interino else ''
        telefono_interino = maestro_interino.telefono or '' if maestro_interino else ''
        codigo_interino = maestro_interino.codigo or '' if maestro_interino else ''
        paterno_interino = maestro_interino.a_paterno or '' if maestro_interino else ''
        materno_interino = maestro_interino.a_materno or '' if maestro_interino else ''
        nombre_interino_solo = maestro_interino.nombres or '' if maestro_interino else ''
        formacion_academica_interino = maestro_interino.form_academica or '' if maestro_interino else ''
        presupuestal_interino = presupuestal_titular
        if motivo_tramite_obj and presupuestal_titular and len(presupuestal_titular) >= 2:
            motivo_text = motivo_tramite_obj.motivo_tramite.upper().strip()
            if motivo_text == "BECA COMISIÓN" or motivo_text == "PRORROGA DE BECA COMISION" or motivo_text == "PRÓRROGA DE BECA COMISIÓN":
                presupuestal_interino = "48" + presupuestal_titular[2:]
            elif motivo_text == "LIC. DE GRAVIDEZ":
                presupuestal_interino = "14" + presupuestal_titular[2:]
            elif motivo_text == "LIC. PREPENSIONARIA":
                presupuestal_interino = "15" + presupuestal_titular[2:]
            elif motivo_text == "PREJUBILATORIO":
                presupuestal_interino = "15" + presupuestal_titular[2:]
        funcion_interino = maestro_titular.funcion or '' if maestro_titular else ''
        folio = form_data.get('folio') or ''
        fecha_efecto1 = form_data.get('fecha_efecto1')
        fecha_efecto2 = form_data.get('fecha_efecto2')
        fecha_efecto3 = form_data.get('fecha_efecto3')
        fecha_efecto4 = form_data.get('fecha_efecto4')
        motivo_movimiento = motivo_tramite_obj.motivo_tramite if motivo_tramite_obj else ''
        observaciones = form_data.get('observaciones') or ''
        quincena_inicial = form_data.get('quincena_inicial') or ''
        quincena_final = form_data.get('quincena_final') or ''
        motivo_tramite_text = motivo_tramite_obj.motivo_tramite.upper().strip() if motivo_tramite_obj else ''
        tipo_movimiento_interino = form_data.get('tipo_movimiento_interino')
        if not tipo_movimiento_interino:
            if motivo_tramite_text == "LIC. DE GRAVIDEZ":
                tipo_movimiento_interino = "ALTA INTERINA EN GRAVIDEZ"
            else:
                if not fecha_efecto3 or not fecha_efecto4:
                    tipo_movimiento_interino = "FECHAS INSUFICIENTES"
                else:
                    diferencia_meses = get_month_diff(fecha_efecto3, fecha_efecto4)
                    if motivo_tramite_text in ["LIC. PREPENSIONARIA", "PREJUBILATORIO"]:
                        if diferencia_meses < 6:
                            tipo_movimiento_interino = "ALTA EN PENSION"
                        else:
                            tipo_movimiento_interino = "ALTA PROVISIONAL"
                    elif motivo_tramite_text in ["BECA COMISIÓN", "PRORROGA DE BECA COMISION", "PRÓRROGA DE BECA COMISIÓN"]:
                        if diferencia_meses < 6:
                            tipo_movimiento_interino = "SUSTITUTO BECARIO"
                        else:
                            tipo_movimiento_interino = "ALTA PROVISIONAL"
                    elif motivo_tramite_text in ["BAJA POR DEFUNCIÓN", "LIC. POR ASUNTOS PARTICULARES", "LIC. POR COM. SINDICAL", "PRORROGA DE LIC. POR COM. SINDICAL", "LIC. POR PASAR A OTRO EMPLEO"]:
                        if diferencia_meses < 6:
                            tipo_movimiento_interino = "ALTA INTERINA LIMITADA"
                        else:
                            tipo_movimiento_interino = "ALTA PROVISIONAL"
                    elif motivo_tramite_text == "JUBILACIÓN":
                        if diferencia_meses < 6:
                            tipo_movimiento_interino = "ALTA INTERINA LIMITADA EN VACANTE DEFINITIVA"
                        else:
                            tipo_movimiento_interino = "ALTA PROVISIONAL EN VACante DEFINITIVA"
                    else:
                        tipo_movimiento_interino = "NO PROCEDENTE"
        today = datetime.now()
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        f_hoy = f"{today.day} de {meses[today.month - 1]} del {today.year}"
        f_hoy_letras = convertir_fecha_a_letras(today)

        fecha_del_calculo_obj = form_data.get('fecha_del_calculo')
        f_calculo = fecha_del_calculo_obj.strftime("%d-%m-%Y") if fecha_del_calculo_obj else ''

        # --- Obtener información de la escuela de adscripción ---
        escuela_adscripcion = maestro_titular.id_escuela if maestro_titular else None
        escuela_adscripcion_info = get_school_info(escuela_adscripcion)
        director_adscripcion_info = get_director_info(escuela_adscripcion) if escuela_adscripcion else {'nombre': 'DIRECTOR NO ENCONTRADO', 'nivel': ''}
        supervisor_adscripcion_info = get_supervisor_info(escuela_adscripcion.zona_esc) if escuela_adscripcion else {'nombre': 'SUPERVISOR NO ENCONTRADO', 'nivel': ''}

        # --- Obtener información de la escuela de pago (Techo Financiero) ---
        escuela_pago = None
        if maestro_titular and maestro_titular.techo_f:
            try:
                escuela_pago = Escuela.objects.get(id_escuela=maestro_titular.techo_f)
            except Escuela.DoesNotExist:
                escuela_pago = None
        escuela_pago_info = get_school_info(escuela_pago)
        director_pago_info = get_director_info(escuela_pago) if escuela_pago else {'nombre': 'DIRECTOR (PAGO) NO ENCONTRADO', 'nivel': ''}
        supervisor_pago_info = get_supervisor_info(escuela_pago.zona_esc) if escuela_pago else {'nombre': 'SUPERVISOR (PAGO) NO ENCONTRADO', 'nivel': ''}

        # --- Lógica para maestros desubicados ---
        # Se determina si el maestro es desubicado para potencialmente usar plantillas especiales,
        # pero ya no se sobrescriben las variables principales del contexto.
        if maestro_titular and maestro_titular.techo_f:
            if not maestro_titular.id_escuela or (maestro_titular.id_escuela and maestro_titular.techo_f.strip().upper() != maestro_titular.id_escuela.id_escuela.strip().upper()):
                is_desubicado = True

        # --- Preparación del contexto para la plantilla ---
        quincena_inicial = form_data.get('quincena_inicial') or ''
        quincena_final = form_data.get('quincena_final') or ''

        # Determinar qué fechas usar para los componentes individuales (Día/Mes/Año)
        # Para ALTA INICIAL (09), usamos las fechas del titular (efecto1 y efecto2)
        if plantilla_tramite.nombre == "ALTA INICIAL (09)":
            ref_fecha_i = fecha_efecto1
            ref_fecha_f = fecha_efecto2
        else:
            ref_fecha_i = fecha_efecto3
            ref_fecha_f = fecha_efecto4

        i_dia = f"{ref_fecha_i.day:02d}" if ref_fecha_i else ''
        i_mes = f"{ref_fecha_i.month:02d}" if ref_fecha_i else ''
        i_ano = ref_fecha_i.year if ref_fecha_i else ''
        f_dia = f"{ref_fecha_f.day:02d}" if ref_fecha_f else ''
        f_mes = f"{ref_fecha_f.month:02d}" if ref_fecha_f else ''
        f_ano = ref_fecha_f.year if ref_fecha_f else ''
        no_prel = form_data.get('no_prel_display') or ''
        folio_prel = form_data.get('folio_prel_display') or ''
        tipo_val = form_data.get('tipo_val_display') or ''
        quienlohizo = get_user_initials(user)

        context = {
            'quienlohizo': quienlohizo,
            'Nombre_Titular': nombre_titular,
            'Prefijo': maestro_titular.nivel_estudio or '' if maestro_titular else '',
            'CURP_Titular': curp_titular,
            'RFC_Titular': rfc_titular,
            'Categoria_Titular': categoria_titular,
            'Presupuestal_Titular': presupuestal_titular,
            'Techo_Financiero': techo_financiero_titular,
            'Categoria_Titular': categoria_titular,
            'Categoria': categoria_titular,
            'Id_Categoria_Titular': maestro_titular.categog.id_categoria if maestro_titular and maestro_titular.categog else '',
            'Horas_Categoria': (maestro_titular.categog.horas.split('.')[0] if maestro_titular and maestro_titular.categog and maestro_titular.categog.horas and '.' in maestro_titular.categog.horas else (maestro_titular.categog.horas if maestro_titular and maestro_titular.categog and maestro_titular.categog.horas else '')),
            'FUNCION_TITULAR': funcion_titular,       
            'Funcion_Titular': funcion_titular,
            'Funcion': funcion_titular,
            'Codigo_Titular': str(codigo_titular),
            'CODIGO_TITULAR': str(codigo_titular),
            'Codigo': str(codigo_titular),
            'Situacion_Titular': "BASE" if str(codigo_titular) == '10' else "INTERINO",
            'Desc_Codigo_Titular': {
                '10': 'BASE',
                '95': 'INTERINO LIMITADO',
                '96': 'INTERINO POR VACANTE DEFINITIVA',
                '09': 'PROVISIONAL',
                '20': 'HONORARIOS',
            }.get(str(codigo_titular), "OTRO"),

            # --- Variables del CT de Adscripción (donde labora) ---
            'Clave_CT': escuela_adscripcion_info['id_escuela'],
            'Nombre_CT': escuela_adscripcion_info['nombre_ct'],
            'Turno': escuela_adscripcion_info['turno'],
            'Domicilio_CT': escuela_adscripcion_info['domicilio'],
            'Z_economica': escuela_adscripcion_info['zona_economica'],
            'Z_Escolar': escuela_adscripcion_info['zona_esc_numero'],
            'Poblacion': escuela_adscripcion_info['region'],
            'U_D': escuela_adscripcion_info['u_d'],
            'Sostenimiento': escuela_adscripcion_info['sostenimiento'],
            'Nom_CTCompleto': escuela_adscripcion_info['nombre_ct'],
            'Supervisor': supervisor_adscripcion_info['nombre'],
            'P_Sup': supervisor_adscripcion_info['nivel'],
            'Director': director_adscripcion_info['nombre'],
            'P_Dir': director_adscripcion_info['nivel'],
            'Municipio': escuela_adscripcion_info['region'],
            'Region': escuela_adscripcion_info['region'],

            # --- Variables explícitas del Techo Financiero (donde se paga) ---
            'Clave_CT_Techo_F': escuela_pago_info['id_escuela'],
            'Nombre_CT_Techo_F': escuela_pago_info['nombre_ct'],
            'Turno_Techo_F': escuela_pago_info['turno'],
            'Domicilio_CT_Techo_F': escuela_pago_info['domicilio'],
            'Poblacion_Techo_F': escuela_pago_info['region'],
            'Nom_CT_Techo_F_Completo': escuela_pago_info['nombre_ct'],
            'Z_economica_Techo_F': form_data.get('ze_techo_f_display') or escuela_pago_info['zona_economica'],
            'Supervisor_Techo_F': supervisor_pago_info['nombre'],
            'P_Sup_Techo_F': supervisor_pago_info['nivel'],
            'Director_Techo_F': director_pago_info['nombre'],
            'P_Dir_Techo_F': director_pago_info['nivel'],
            
            # --- Resto del contexto ---
            'T_Movimiento': motivo_movimiento,
            'Efecto_1': fecha_efecto1.strftime("%d/%m/%Y") if fecha_efecto1 else '',
            'Efecto_1_Letra': f"{fecha_efecto1.day} de {meses[fecha_efecto1.month - 1]} del {fecha_efecto1.year}" if fecha_efecto1 else '',
            'Efecto_2': fecha_efecto2.strftime("%d/%m/%Y") if fecha_efecto2 else '',
            'Efecto_3': format_date_for_solicitud_asignacion(fecha_efecto3) if plantilla_tramite.nombre == "SOLICITUD DE ASIGNACION" else (fecha_efecto3.strftime("%d/%m/%Y") if fecha_efecto3 else ''),
            'Efecto_4': format_date_for_solicitud_asignacion(fecha_efecto4) if plantilla_tramite.nombre == "SOLICITUD DE ASIGNACION" else (fecha_efecto4.strftime("%d/%m/%Y") if fecha_efecto4 else ''),
            'F_Hoy': f_hoy,
            'F_OfPres': folio,
            'F_Calculo': f_calculo, # Added F_Calculo here
            'F2_Calculo': form_data.get('F2_Calculo', ''),
            'COMENTARIOS': observaciones,
            'Nombre_Interino': nombre_interino,
            'CURP_Interino': curp_interino,
            'RFC_Interino': rfc_interino,
            'Dom_Particular': domicilio_part_titular if plantilla_tramite.nombre == "ALTA INICIAL (09)" else domicilio_part_interino,
            'C_P_Interino': codigo_postal_titular if plantilla_tramite.nombre == "ALTA INICIAL (09)" else codigo_postal_interino,
            'Poblacion_Interino': poblacion_titular if plantilla_tramite.nombre == "ALTA INICIAL (09)" else poblacion_interino,
            'Telefono_Interino': telefono_titular if plantilla_tramite.nombre == "ALTA INICIAL (09)" else telefono_interino,
            'Presupuestal_Interino': presupuestal_interino,
            'Funcion_Interino': funcion_interino,
            'Tipo_Movimiento_Interino': tipo_movimiento_interino,
            'Codigo_Interino': codigo_interino,
            # Para ALTA INICIAL usamos apellidos y nombres del TITULAR, para el resto los del INTERINO
            'Paterno': paterno_titular if plantilla_tramite.nombre == "ALTA INICIAL (09)" else paterno_interino,
            'Materno': materno_titular if plantilla_tramite.nombre == "ALTA INICIAL (09)" else materno_interino,
            'Nombre': nombre_titular_solo if plantilla_tramite.nombre == "ALTA INICIAL (09)" else nombre_interino_solo,
            'Formacion_Academica': formacion_academica_interino,
            'No_Prel': no_prel,
            'Folio_Prel': folio_prel,
            'Tipo_Val': tipo_val,
            'Resultado_Alta': tipo_movimiento_interino,
            'QuincenaInicial': '',
            'QuincenaFinal': '',
            'Horario': maestro_titular.horario if maestro_titular else '',
            'Horario_Turno': "08:00 a 13:00 Hrs." if (escuela_adscripcion_info['turno'] or '').upper() in ('MATUTINO', 'DISCONTINUO') else ("14:00 a 19:00 Hrs." if (escuela_adscripcion_info['turno'] or '').upper() == 'VESPERTINO' else ''),
            'TipoPlaza': 'JORNADA' if (maestro_titular and maestro_titular.hrs == "00.0") else "HORA/SEMANA/MES",
            'Horas': maestro_titular.hrs.split('.')[0] if (maestro_titular and maestro_titular.hrs and '.' in maestro_titular.hrs) else '',
            'Nivel': 'Educación Especial',
            'Entidad': 'DURANGO',
            'Destino': '',
            'Apreciacion': '',
            'TipoVacante': '',
            'NoOrdenamiento': '',
            'FolioOrdenamiento': '',
            'CurpInterino': curp_interino,
            'NombreInterino': nombre_interino,
            'Tipo': motivo_movimiento,
            'Observaciones': observaciones,
            'QuincenaInicio': quincena_inicial,
            'QuincenaFinal': quincena_final,
            'I_Dia': i_dia,
            'I_Mes': i_mes,
            'I_Ano': i_ano,
            'F_Dia': f_dia,
            'F_Mes': f_mes,
            'F_Ano': f_ano,
            'F_HoyLetra': f_hoy_letras,
            'fecha_al_corte': form_data.get('fecha_al_corte', '').strftime("%d/%m/%Y") if form_data.get('fecha_al_corte') else '', # Added new fields to context
            'antiguedad_funcion': form_data.get('antiguedad_funcion', '') ,
            'antiguedad_categoria': form_data.get('antiguedad_categoria', '') ,
            'antiguedad_servicio': form_data.get('antiguedad_servicio', '') ,
            'fecha_adscripcion': form_data.get('fecha_adscripcion', '').strftime("%d/%m/%Y") if form_data.get('fecha_adscripcion') else '',
            'incentivos': form_data.get('incentivos', '') ,
            'Formacion_Titular': form_data.get('form_academica_titular_display') or (maestro_titular.form_academica if maestro_titular else ''),
            'Sustituida': form_data.get('sustituida_nombre', ''),
            # --- Variables dedicadas para CAMBIO DE EFECTOS ---
            # Clave presupuestal propia del interino (sin modificacion por motivo)
            'Presupuestal_Interino_Propio': maestro_interino.clave_presupuestal if maestro_interino else '',
            # Techo financiero del interino (CCT donde se paga al interino)
            'Techo_Financiero_Interino': maestro_interino.techo_f if maestro_interino else '',
        }

        # Sobrescribir contexto con escuela destino para PRESENTACION LABORAL PARA CAMBIO DE ADSCRIPCION
        dest_escuela = form_data.get('_dest_escuela')
        if dest_escuela and template_name_upper == 'PRESENTACION LABORAL PARA CAMBIO DE ADSCRIPCION':
            dest_info = get_school_info(dest_escuela)
            dest_director = get_director_info(dest_escuela)
            dest_supervisor = get_supervisor_info(dest_escuela.zona_esc) if dest_escuela.zona_esc else {'nombre': '', 'nivel': ''}
            context.update({
                'Clave_CT': dest_info['id_escuela'],
                'Nombre_CT': dest_info['nombre_ct'],
                'Nom_CTCompleto': dest_info['nombre_ct'],
                'Turno': dest_info['turno'],
                'Domicilio_CT': dest_info['domicilio'],
                'Poblacion': dest_info['region'],
                'Z_economica': dest_info['zona_economica'],
                'Z_Escolar': dest_info['zona_esc_numero'],
                'Director': dest_director['nombre'],
                'P_Dir': dest_director['nivel'],
                'Supervisor': dest_supervisor['nombre'],
                'P_Sup': dest_supervisor['nivel'],
            })

        doc.render(context)
        output_base_dir = os.path.join(settings.BASE_DIR, 'tramites_generados')
        template_name_clean = plantilla_tramite.nombre.replace(" ", "_").replace(".", "").replace("(", "").replace(")", "").replace(",", "").replace("-", "").upper()
        subfolder_map = {
            "REINGRESO": "reingresos",
            "FILIACION": "filiacion",
            "SOLICITUD_DE_ASIGNACION": "solicitud_asignacion",
            "REINGRESO_SIN_PRELACION": "reingreso_sin_prelacion",
            "JUSTIFICACION_DE_PERFIL": "justificacion_perfil",
            "REPORTE_DE_VACANCIA": "reporte_vacancia",
            "CONSTANCIAS": "constancias",
            "CAMBIO_DEL_CENTRO_DE_TRABAJO": "cambio_ct",
            "CUADRO_CAMBIOS_CON_FOLIO": "cuadro_cambios",
            "PROPUESTA_DE_MOVIMIENTO": "propuesta_movimiento",
            "OFICIO_DE_REINCORPORACION": "oficio_reincorporacion",
            "PRESENTACION_LABORAL": "presentacion_laboral",
            "PRESENTACION_LABORAL_PARA_CAMBIO_DE_ADSCRIPCION": "presentacion_laboral_cambio_adscripcion",
            "SOLICITUD_BECA_COMISION": "solicitud_beca_comision",
            "LIBERACION_DE_SUPERVISORES": "liberacion_supervisores",
            "CAPTURA_DE_GRAVIDEZ": "captura_gravidez",
            "CAMBIO_DE_EFECTOS": "cambio_efectos",
            "ALTA_INICIAL_09": "alta_inicial",
        }
        subfolder = subfolder_map.get(template_name_clean, "otros_tramites")
        output_dir = os.path.join(output_base_dir, subfolder)
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"TRAMITE_{template_name_clean}_{timestamp}.docx"
        output_path = os.path.join(output_dir, output_filename)
        doc.save(output_path)
        return True, output_path
    except Exception as e:
        print(f"Error generating Word document: {e}")
        return False, str(e)