import os
import openpyxl
from docxtpl import DocxTemplate
from datetime import datetime, date
from django.conf import settings
import gspread
from google.oauth2 import service_account

# Asegúrate de que los modelos necesarios estén disponibles.
# A veces es mejor pasar los objetos como argumentos en lugar de importarlos directamente
# para evitar dependencias circulares, pero por ahora los importamos.
from ..models import Maestro, Escuela

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

# Helper function to get director
def get_director_info(escuela):
    if not escuela: return {'nombre': 'DIRECTOR NO ENCONTRADO', 'nivel': ''}
    director = Maestro.objects.filter(id_escuela=escuela, funcion__in=['DIRECTOR', 'DIRECTOR (A)']).first()
    if director:
        return {'nombre': get_full_name(director), 'nivel': director.nivel_estudio or ''}
    return {'nombre': 'DIRECTOR NO ENCONTRADO', 'nivel': ''}

# Helper function to get supervisor
def get_supervisor_info(zona):
    if not zona: return {'nombre': 'SUPERVISOR NO ENCONTRADO', 'nivel': ''}
    supervisor = Maestro.objects.filter(id_escuela__zona_esc=zona, funcion__in=['SUPERVISOR', 'SUPERVISOR (A)', 'SUPERVISOR(A)']).first()
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
    print("DEBUG GS: Iniciando envío a Google Sheets...")
    try:
        if not hasattr(settings, 'GOOGLE_SHEETS_CREDENTIALS'):
            return False, "Configuración de credenciales no encontrada"
        creds_json = settings.GOOGLE_SHEETS_CREDENTIALS
        if not creds_json.get('private_key') or not creds_json.get('client_email'):
            return False, "Credenciales incompletas - falta private_key o client_email"
        print(f"DEBUG GS: Usando cuenta: {creds_json['client_email']}")
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = service_account.Credentials.from_service_account_info(creds_json, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        print("DEBUG GS: ✅ Autenticación exitosa")
        spreadsheet = gc.open_by_key(settings.GOOGLE_SHEET_ID)
        worksheet = spreadsheet.worksheet(settings.GOOGLE_SHEET_WORKSHEET_NAME)
        print("DEBUG GS: ✅ Hoja abierta correctamente")
        cleaned_data = []
        for item in row_data:
            if item is None:
                cleaned_data.append('')
            elif isinstance(item, (date, datetime)):
                cleaned_data.append(item.strftime('%Y-%m-%d'))
            else:
                cleaned_data.append(str(item))
        worksheet.append_row(cleaned_data)
        print(f"DEBUG GS: ✅ Fila agregada: {cleaned_data}")
        return True, "Datos enviados correctamente a Google Sheets"
    except gspread.exceptions.SpreadsheetNotFound:
        error_msg = "Google Sheet no encontrado. Verifica el GOOGLE_SHEET_ID."
        print(f"DEBUG GS: ❌ {error_msg}")
        return False, error_msg
    except gspread.exceptions.WorksheetNotFound:
        error_msg = f"Hoja '{settings.GOOGLE_SHEET_WORKSHEET_NAME}' no encontrada."
        print(f"DEBUG GS: ❌ {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"DEBUG GS: ❌ {error_msg}")
        return False, error_msg

def generate_word_document(form_data, plantilla_tramite, user):
    try:
        maestro_titular = form_data.get('maestro_titular')
        template_name_upper = plantilla_tramite.nombre.upper().strip()
        ruta_plantilla_final = plantilla_tramite.ruta_archivo
        is_desubicado = False
        if maestro_titular and maestro_titular.techo_f and maestro_titular.id_escuela:
            if maestro_titular.techo_f.strip().upper() != maestro_titular.id_escuela.id_escuela.strip().upper():
                is_desubicado = True
        plantillas_especiales = {
            "REINGRESO": "REINGRESODESUBICADO.docx",
            "FILIACION": "FILIACIONDESUBICADO.docx",
        }
        if template_name_upper in plantillas_especiales and is_desubicado:
            nueva_plantilla = plantillas_especiales[template_name_upper]
            ruta_plantilla_final = nueva_plantilla
            print(f"DEBUG: Maestro desubicado detectado para {template_name_upper}. Usando plantilla especial: {ruta_plantilla_final}")
        template_path = os.path.join(settings.BASE_DIR, 'tramites', 'Plantillas', 'Word', ruta_plantilla_final)
        doc = DocxTemplate(template_path)
        maestro_interino = form_data.get('maestro_interino')
        motivo_tramite_obj = form_data.get('motivo_tramite')
        nombre_titular = get_full_name(maestro_titular)
        curp_titular = maestro_titular.curp or '' if maestro_titular else ''
        rfc_titular = maestro_titular.rfc or '' if maestro_titular else ''
        categoria_titular = maestro_titular.categog.descripcion if maestro_titular and maestro_titular.categog else ''
        presupuestal_titular = maestro_titular.clave_presupuestal or '' if maestro_titular else ''
        techo_financiero_titular = maestro_titular.techo_f or '' if maestro_titular else ''
        funcion_titular = maestro_titular.funcion or '' if maestro_titular else ''
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
            if motivo_text == "BECA COMISIÓN" or motivo_text == "PRORROGA DE BECA COMISION":
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
        tipo_movimiento_interino = ""
        if motivo_tramite_text == "LIC. DE GRAVIDEZ":
            tipo_movimiento_interino = "ALTA INTERINA EN GRAVIDEZ"
        elif motivo_tramite_text == "LIC. POR PASAR A OTRO EMPLEO":
            tipo_movimiento_interino = "ALTA INICIAL POR PROMOCIÓN O ADMISIÓN"
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
                elif motivo_tramite_text in ["BAJA POR DEFUNCIÓN", "LIC. POR ASUNTOS PARTICULARES", "LIC. POR COM. SINDICAL", "PRORROGA DE LIC. POR COM. SINDICAL"]:
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
        escuela_adscripcion = None
        if maestro_titular:
            escuela_adscripcion = maestro_titular.id_escuela
        escuela_adscripcion_info = get_school_info(escuela_adscripcion)
        if escuela_adscripcion:
            director_adscripcion_info = get_director_info(escuela_adscripcion)
            supervisor_adscripcion_info = get_supervisor_info(escuela_adscripcion.zona_esc)
        else:
            director_adscripcion_info = {'nombre': 'DIRECTOR NO ENCONTRADO', 'nivel': ''}
            supervisor_adscripcion_info = {'nombre': 'SUPERVISOR NO ENCONTRADO', 'nivel': ''}
        escuela_pago = None
        if maestro_titular and maestro_titular.techo_f:
            try:
                escuela_pago = Escuela.objects.get(id_escuela=maestro_titular.techo_f)
            except Escuela.DoesNotExist:
                escuela_pago = None
        escuela_pago_info = get_school_info(escuela_pago)
        if escuela_pago:
            director_pago_info = get_director_info(escuela_pago)
            supervisor_pago_info = get_supervisor_info(escuela_pago.zona_esc)
        else:
            director_pago_info = {'nombre': 'DIRECTOR (PAGO) NO ENCONTRADO', 'nivel': ''}
            supervisor_pago_info = {'nombre': 'SUPERVISOR (PAGO) NO ENCONTRADO', 'nivel': ''}
        quincena_inicial = form_data.get('quincena_inicial') or ''
        quincena_final = form_data.get('quincena_final') or ''
        i_dia = f"{fecha_efecto3.day:02d}" if fecha_efecto3 else ''
        i_mes = f"{fecha_efecto3.month:02d}" if fecha_efecto3 else ''
        i_ano = fecha_efecto3.year if fecha_efecto3 else ''
        f_dia = f"{fecha_efecto4.day:02d}" if fecha_efecto4 else ''
        f_mes = f"{fecha_efecto4.month:02d}" if fecha_efecto4 else ''
        f_ano = fecha_efecto4.year if fecha_efecto4 else ''
        no_prel = form_data.get('no_prel_display') or ''
        folio_prel = form_data.get('folio_prel_display') or ''
        tipo_val = form_data.get('tipo_val_display') or ''
        quienlohizo = get_user_initials(user)
        context = {
            'quienlohizo': quienlohizo,
            'Nombre_Titular': nombre_titular,
            'CURP_Titular': curp_titular,
            'RFC_Titular': rfc_titular,
            'Categoria_Titular': categoria_titular,
            'Presupuestal_Titular': presupuestal_titular,
            'Techo_Financiero': techo_financiero_titular,
            'Funcion_Titular': funcion_titular,
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
            'Clave_CT_Techo_F': escuela_pago_info['id_escuela'],
            'Nombre_CT_Techo_F': escuela_pago_info['nombre_ct'],
            'Turno_Techo_F': escuela_pago_info['turno'],
            'Domicilio_CT_Techo_F': escuela_pago_info['domicilio'],
            'Poblacion_Techo_F': escuela_pago_info['region'],
            'Nom_CT_Techo_F_Completo': escuela_pago_info['nombre_ct'],
            'T_Movimiento': motivo_movimiento,
            'Efecto_1': fecha_efecto1.strftime("%d/%m/%Y") if fecha_efecto1 else '',
            'Efecto_2': fecha_efecto2.strftime("%d/%m/%Y") if fecha_efecto2 else '',
            'Efecto_3': format_date_for_solicitud_asignacion(fecha_efecto3) if plantilla_tramite.nombre == "SOLICITUD DE ASIGNACION" else (fecha_efecto3.strftime("%d/%m/%Y") if fecha_efecto3 else ''),
            'Efecto_4': format_date_for_solicitud_asignacion(fecha_efecto4) if plantilla_tramite.nombre == "SOLICITUD DE ASIGNACION" else (fecha_efecto4.strftime("%d/%m/%Y") if fecha_efecto4 else ''),
            'F_Hoy': f_hoy,
            'F_OfPres': folio,
            'COMENTARIOS': observaciones,
            'Nombre_Interino': nombre_interino,
            'CURP_Interino': curp_interino,
            'RFC_Interino': rfc_interino,
            'Dom_Particular': domicilio_part_interino,
            'C_P_Interino': codigo_postal_interino,
            'Poblacion_Interino': poblacion_interino,
            'Telefono_Interino': telefono_interino,
            'Presupuestal_Interino': presupuestal_interino,
            'Funcion_Interino': funcion_interino,
            'Tipo_Movimiento_Interino': tipo_movimiento_interino,
            'Codigo_Interino': codigo_interino,
            'Paterno': paterno_interino,
            'Materno': materno_interino,
            'Nombre': nombre_interino_solo,
            'Formacion_Academica': formacion_academica_interino,
            'No_Prel': no_prel,
            'Folio_Prel': folio_prel,
            'Tipo_Val': tipo_val,
            'Supervisor': supervisor_adscripcion_info['nombre'],
            'P_Sup': supervisor_adscripcion_info['nivel'],
            'Director': director_adscripcion_info['nombre'],
            'P_Dir': director_adscripcion_info['nivel'],
            'Supervisor_Techo_F': supervisor_pago_info['nombre'],
            'P_Sup_Techo_F': supervisor_pago_info['nivel'],
            'Director_Techo_F': director_pago_info['nombre'],
            'P_Dir_Techo_F': director_pago_info['nivel'],
            'Resultado_Alta': tipo_movimiento_interino,
            'QuincenaInicial': '',
            'QuincenaFinal': '',
            'Horario': maestro_titular.horario if maestro_titular else '',
            'TipoPlaza': 'JORNADA' if (maestro_titular and maestro_titular.hrs == "00.0") else "HORA/SEMANA/MES",
            'Horas': maestro_titular.hrs.split('.')[0] if (maestro_titular and maestro_titular.hrs and '.' in maestro_titular.hrs) else '',
            'Nivel': 'Educación Especial',
            'Entidad': 'DURANGO',
            'Municipio': escuela_adscripcion_info['region'],
            'Region': escuela_adscripcion_info['region'],
            'ZonaEconomica': escuela_adscripcion_info['zona_economica'],
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
        }
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
