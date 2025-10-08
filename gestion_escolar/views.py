from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy
from django.utils import timezone

from django.contrib.auth.models import Group, User
from .forms import (ZonaForm, EscuelaForm, MaestroForm, CategoriaForm, TramiteForm, 
                   SignUpForm, VacanciaForm, DocumentoExpedienteForm, 
                   CustomUserChangeForm, AsignarDirectorForm, PendienteForm, CorrespondenciaForm)
from .models import (Zona, Escuela, Maestro, Categoria, MotivoTramite, 
                   PlantillaTramite, Prelacion, LoteReporteVacancia, Vacancia, 
                   TipoApreciacion, Historial, DocumentoExpediente, 
                   Correspondencia, Notificacion, Pendiente)
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
import csv
import json
import os
import openpyxl
from docxtpl import DocxTemplate
from datetime import datetime, date
from django.conf import settings



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

# Helper function to calculate month difference similar to VBA DateDiff("m", ...)
def get_month_diff(d1, d2):
    # Ensure d1 is earlier than d2
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
    if num < 1000000: # For years like 2025
        miles = num // 1000
        resto = num % 1000
        if miles == 1:
            letras = "mil"
        else:
            letras = numero_a_letras_general(miles) + " mil"
        if resto > 0:
            letras += " " + numero_a_letras_general(resto)
        return letras
    return str(num) # Fallback for very large numbers

def convertir_fecha_a_letras(fecha):
    dia = numero_a_letras_general(fecha.day)
    meses_letras = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    mes = meses_letras[fecha.month - 1]
    anio = numero_a_letras_general(fecha.year)

    return f"{dia} de {mes} del {anio}"

def serialize_form_data(cleaned_data):
    """
    Converts form.cleaned_data into a JSON-serializable dictionary,
    handling model instances and date objects.
    """
    serialized_data = {}
    for key, value in cleaned_data.items():
        if hasattr(value, 'pk'):  # It's a Django model instance
            serialized_data[key] = value.pk
        elif isinstance(value, (date, datetime)):
            serialized_data[key] = value.isoformat()
        elif isinstance(value, dict): # Recursively handle nested dictionaries
            serialized_data[key] = serialize_form_data(value)
        elif isinstance(value, list): # Handle lists of serializable items
            serialized_data[key] = [
                item.pk if hasattr(item, 'pk') else
                item.isoformat() if isinstance(item, (date, datetime)) else
                item
                for item in value
            ]
        else:
            serialized_data[key] = value
    return serialized_data

# Main Word generation function
def generate_word_document(form_data, plantilla_tramite):
    try:
        # --- Construct absolute path for the template ---
        template_path = os.path.join(settings.BASE_DIR, 'tramites', 'Plantillas', 'Word', plantilla_tramite.ruta_archivo)
        doc = DocxTemplate(template_path)

        # --- Gather Data ---
        maestro_titular = form_data.get('maestro_titular')
        maestro_interino = form_data.get('maestro_interino')
        motivo_tramite_obj = form_data.get('motivo_tramite')

        # Data from Maestro Titular
        nombre_titular = get_full_name(maestro_titular)
        curp_titular = maestro_titular.curp or '' if maestro_titular else ''
        rfc_titular = maestro_titular.rfc or '' if maestro_titular else ''
        categoria_titular = maestro_titular.categog.descripcion if maestro_titular and maestro_titular.categog else ''
        presupuestal_titular = maestro_titular.clave_presupuestal or '' if maestro_titular else ''
        techo_financiero_titular = maestro_titular.techo_f or '' if maestro_titular else ''
        funcion_titular = maestro_titular.funcion or '' if maestro_titular else ''

        # Data from Maestro Interino
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
        
        # Lógica para presupuestal_interino
        presupuestal_interino = presupuestal_titular
        if motivo_tramite_obj and presupuestal_titular and len(presupuestal_titular) >= 2:
            motivo_text = motivo_tramite_obj.motivo_tramite.upper().strip()
            if motivo_text == "BECA COMISIÓN" or motivo_text == "PRORROGA DE BECA COMISION":
                presupuestal_interino = "48" + presupuestal_titular[2:]
            elif motivo_text == "LIC. DE GRAVIDEZ":
                presupuestal_interino = "24" + presupuestal_titular[2:]
        
        # Lógica para funcion_interino
        funcion_interino = maestro_titular.funcion or '' if maestro_titular else ''

        # Data from Form fields
        folio = form_data.get('folio') or ''
        fecha_efecto1 = form_data.get('fecha_efecto1')
        fecha_efecto2 = form_data.get('fecha_efecto2')
        fecha_efecto3 = form_data.get('fecha_efecto3')
        fecha_efecto4 = form_data.get('fecha_efecto4')
        motivo_movimiento = motivo_tramite_obj.motivo_tramite if motivo_tramite_obj else ''
        observaciones = form_data.get('observaciones') or ''
        quincena_inicial = form_data.get('quincena_inicial') or ''
        quincena_final = form_data.get('quincena_final') or ''

        # Lógica para calcular tipo_movimiento_interino
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
                elif motivo_tramite_text == "BECA COMISIÓN":
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

        # Dynamic Dates
        today = datetime.now()
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        f_hoy = f"{today.day} de {meses[today.month - 1]} del {today.year}"
        f_hoy_letras = convertir_fecha_a_letras(today)

        # Director, Supervisor, and School Info
        escuela_titular = maestro_titular.id_escuela if maestro_titular else None
        escuela_info = get_school_info(escuela_titular)
        director_info = get_director_info(escuela_titular)
        supervisor_info = get_supervisor_info(escuela_titular.zona_esc if escuela_titular else None)

        quincena_inicial = form_data.get('quincena_inicial') or ''
        quincena_final = form_data.get('quincena_final') or ''

        # Extract day, month, year for [I_Dia], [I_Mes], [I_Ano]
        i_dia = f"{fecha_efecto3.day:02d}" if fecha_efecto3 else ''
        i_mes = f"{fecha_efecto3.month:02d}" if fecha_efecto3 else '' # Month as number
        i_ano = fecha_efecto3.year if fecha_efecto3 else ''

        # Extract day, month, year for [F_Dia], [F_Mes], [F_Ano]
        f_dia = f"{fecha_efecto4.day:02d}" if fecha_efecto4 else ''
        f_mes = f"{fecha_efecto4.month:02d}" if fecha_efecto4 else '' # Month as number
        f_ano = fecha_efecto4.year if fecha_efecto4 else ''

        # Obtener datos de prelación del formulario
        no_prel = form_data.get('no_prel_display') or ''
        folio_prel = form_data.get('folio_prel_display') or ''
        tipo_val = form_data.get('tipo_val_display') or ''

        # --- Context for docxtpl ---
        context = {
            'Nombre_Titular': nombre_titular,
            'CURP_Titular': curp_titular,
            'RFC_Titular': rfc_titular,
            'Categoria_Titular': categoria_titular,
            'Presupuestal_Titular': presupuestal_titular,
            'Techo_Financiero': techo_financiero_titular,
            'Funcion_Titular': funcion_titular,
            'Clave_CT': escuela_info['id_escuela'],
            'Nombre_CT': escuela_info['nombre_ct'],
            'Turno': escuela_info['turno'],
            'Domicilio_CT': escuela_info['domicilio'],
            'Z_economica': escuela_info['zona_economica'],
            'Z_Escolar': escuela_info['zona_esc_numero'],
            'Poblacion': escuela_info['region'],
            'U_D': escuela_info['u_d'],
            'Sostenimiento': escuela_info['sostenimiento'],

            'T_Movimiento': motivo_movimiento,
            'Efecto_1': fecha_efecto1.strftime("%d/%m/%Y") if fecha_efecto1 else '',
            'Efecto_2': fecha_efecto2.strftime("%d/%m/%Y") if fecha_efecto2 else '',
            'Efecto_3': fecha_efecto3.strftime("%d/%m/%Y") if fecha_efecto3 else '',
            'Efecto_4': fecha_efecto4.strftime("%d/%m/%Y") if fecha_efecto4 else '',
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

            # Prelacion Data (ahora se llenan automáticamente)
            'No_Prel': no_prel,
            'Folio_Prel': folio_prel,
            'Tipo_Val': tipo_val,

            # Autoridades
            'Supervisor': supervisor_info['nombre'],
            'P_Sup': supervisor_info['nivel'],
            'Director': director_info['nombre'],
            'P_Dir': director_info['nivel'],

            # VBA specific fields
            'Resultado_Alta': tipo_movimiento_interino,
            'QuincenaInicial': '',
            'QuincenaFinal': '',
            'Horario': maestro_titular.horario if maestro_titular else '',
            'TipoPlaza': 'JORNADA' if (maestro_titular and maestro_titular.hrs == "00.0") else "HORA/SEMANA/MES",
            'Horas': maestro_titular.hrs.split('.')[0] if (maestro_titular and maestro_titular.hrs and '.' in maestro_titular.hrs) else '',
            'Nivel': 'Educación Especial',
            'Entidad': 'DURANGO',
            'Municipio': escuela_info['region'],
            'Region': escuela_info['region'],
            'ZonaEconomica': escuela_info['zona_economica'],
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
            'Nom_CTCompleto': escuela_info['nombre_ct'],
        }

        # --- Render Document ---
        doc.render(context)

        # --- Save Document ---
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

# Vista AJAX para obtener datos de prelación
def get_prelacion_data_ajax(request):
    curp_interino = request.GET.get('curp_interino')
    datos_prelacion = {
        'encontrado': False,
        'numero_prelacion': '',
        'folio_prelacion': '',
        'tipo_val': '',
        'nombre_prelacion': ''
    }

    if curp_interino:
        try:
            # Buscar en la tabla Prelacion por la CURP del interino
            prelacion = Prelacion.objects.filter(curp=curp_interino).first()
            
            if prelacion:
                datos_prelacion = {
                    'encontrado': True,
                    'numero_prelacion': prelacion.pos_orden or '',
                    'folio_prelacion': prelacion.folio or '',
                    'tipo_val': prelacion.tipo_val or '',
                    'nombre_prelacion': prelacion.nombre or ''
                }
        except Exception as e:
            print(f"Error buscando prelación: {e}")

    return JsonResponse(datos_prelacion)

# Vistas principales
def index(request):
    total_zonas = Zona.objects.count()
    total_escuelas = Escuela.objects.count()
    total_maestros = Maestro.objects.count()
    total_directores = Maestro.objects.filter(funcion__icontains='DIRECTOR').count()

    distribucion_por_zona = Zona.objects.annotate(num_escuelas=Count('escuela')).order_by('numero')

    zona_labels = [f"Zona {zona.numero}" for zona in distribucion_por_zona]
    zona_data = [zona.num_escuelas for zona in distribucion_por_zona]

    ultimo_personal = Maestro.objects.order_by('-fecha_registro')[:5]

    context = {
        'total_zonas': total_zonas,
        'total_escuelas': total_escuelas,
        'total_maestros': total_maestros,
        'total_directores': total_directores,
        'ultimo_personal': ultimo_personal,
        'zona_labels': json.dumps(zona_labels),
        'zona_data': json.dumps(zona_data),
        'titulo': 'Dashboard'
    }
    return render(request, 'gestion_escolar/index.html', context)

@login_required
def ajustes_view(request):
    return render(request, 'gestion_escolar/ajustes.html', {'titulo': 'Ajustes'})


@login_required
def cambiar_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Tu contraseña ha sido actualizada correctamente.')
            return redirect('ajustes')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'gestion_escolar/cambiar_password.html', {
        'form': form,
        'titulo': 'Cambiar Contraseña'
    })

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado correctamente.')
            return redirect('ajustes')
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, 'gestion_escolar/editar_perfil.html', {'form': form, 'titulo': 'Editar Perfil'})


@user_passes_test(lambda u: u.is_superuser)
def asignar_director(request):
    if request.method == 'POST':
        form = AsignarDirectorForm(request.POST)
        if form.is_valid():
            maestro = form.cleaned_data['maestro']
            user = form.cleaned_data['usuario']
            
            maestro.user = user
            maestro.save()
            
            directores_group, created = Group.objects.get_or_create(name='Directores')
            user.groups.add(directores_group)
            
            messages.success(request, f'El maestro {maestro} ha sido asignado como director al usuario {user}.')
            return redirect('ajustes')
    else:
        form = AsignarDirectorForm()
    return render(request, 'gestion_escolar/asignar_director.html', {'form': form, 'titulo': 'Asignar Director'})


# Vistas para Zonas
def lista_zonas(request):
    if request.user.groups.filter(name='Directores').exists():
        raise PermissionDenied
    
    # Usamos select_related para traer el supervisor en la misma consulta
    zonas = Zona.objects.select_related('supervisor').order_by('numero')

    return render(request, 'gestion_escolar/lista_zonas.html', {'zonas': zonas})

def agregar_zona(request):
    if request.method == 'POST':
        form = ZonaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Zona agregada correctamente.')
            return redirect('lista_zonas')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = ZonaForm()
    return render(request, 'gestion_escolar/form_zona.html', {'form': form, 'titulo': 'Agregar Zona'})

def editar_zona(request, pk):
    zona = get_object_or_404(Zona.objects.select_related('supervisor'), pk=pk)
    if request.method == 'POST':
        form = ZonaForm(request.POST, instance=zona)
        if form.is_valid():
            form.save()
            messages.success(request, 'Zona actualizada correctamente.')
            return redirect('lista_zonas')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = ZonaForm(instance=zona)
    
    return render(request, 'gestion_escolar/form_zona.html', {
        'form': form, 
        'zona': zona, 
        'titulo': 'Editar Zona'
    })

def eliminar_zona(request, pk):
    zona = get_object_or_404(Zona, pk=pk)
    if request.method == 'POST':
        zona.delete()
        messages.success(request, 'Zona eliminada correctamente.')
        return redirect('lista_zonas')
    return render(request, 'gestion_escolar/eliminar_zona.html', {'zona': zona})

def detalle_zona(request, pk):
    # Usamos select_related para optimizar y traer el supervisor en la misma consulta
    zona = get_object_or_404(Zona.objects.select_related('supervisor'), pk=pk)
    
    # Obtenemos todas las escuelas que pertenecen a esta zona
    escuelas_en_zona = Escuela.objects.filter(zona_esc=zona).order_by('nombre_ct')
    
    context = {
        'zona': zona,
        'escuelas': escuelas_en_zona,
        'titulo': f"Detalle de la Zona {zona.numero}"
    }
    
    return render(request, 'gestion_escolar/detalle_zona.html', context)


# Vistas para Escuelas
def lista_escuelas(request):
    if request.user.groups.filter(name='Directores').exists():
        raise PermissionDenied
    escuelas = Escuela.objects.all().order_by('nombre_ct')
    return render(request, 'gestion_escolar/lista_escuelas.html', {'escuelas': escuelas})

def agregar_escuela(request):
    if request.method == 'POST':
        form = EscuelaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Escuela agregada correctamente.')
            return redirect('lista_escuelas')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = EscuelaForm()
    return render(request, 'gestion_escolar/form_escuela.html', {'form': form, 'titulo': 'Agregar Escuela'})

def editar_escuela(request, pk):
    escuela = get_object_or_404(Escuela, pk=pk)
    if request.method == 'POST':
        form = EscuelaForm(request.POST, instance=escuela)
        if form.is_valid():
            form.save()
            messages.success(request, 'Escuela actualizada correctamente.')
            return redirect('lista_escuelas')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = EscuelaForm(instance=escuela)
    return render(request, 'gestion_escolar/form_escuela.html', {'form': form, 'titulo': 'Editar Escuela'})

def eliminar_escuela(request, pk):
    escuela = get_object_or_404(Escuela, pk=pk)
    if request.method == 'POST':
        escuela.delete()
        messages.success(request, 'Escuela eliminada correctamente.')
        return redirect('lista_escuelas')
    return render(request, 'gestion_escolar/eliminar_escuela.html', {'escuela': escuela})

def detalle_escuela(request, pk):
    escuela = get_object_or_404(Escuela, pk=pk)
    personal = Maestro.objects.filter(id_escuela=escuela)
    context = {
        'escuela': escuela,
        'personal': personal,
        'titulo': 'Detalle de la Escuela'
    }
    return render(request, 'gestion_escolar/detalle_escuela.html', context)

# Vistas para Maestros
@login_required
def lista_maestros(request):
    user = request.user
    if user.groups.filter(name='Directores').exists():
        try:
            # Director can only see their school's teachers
            maestro_director = user.maestro_profile
            escuela_director = maestro_director.id_escuela
            maestros = Maestro.objects.filter(id_escuela=escuela_director).exclude(
                id_maestro__isnull=True
            ).exclude(
                id_maestro=''
            ).order_by('a_paterno', 'a_materno', 'nombres')
        except AttributeError:
            # Handle case where user is in Directores group but has no maestro_profile
            maestros = Maestro.objects.none()
    else:
        # Admin and other users can see all teachers
        maestros = Maestro.objects.exclude(
            id_maestro__isnull=True
        ).exclude(
            id_maestro=''
        ).order_by('a_paterno', 'a_materno', 'nombres')
        
    return render(request, 'gestion_escolar/lista_maestros.html', {'maestros': maestros})

def agregar_maestro(request):
    all_escuelas = Escuela.objects.all()
    initial_data = {}
    escuela_id = request.GET.get('escuela_id')
    if escuela_id:
        try:
            escuela = Escuela.objects.get(pk=escuela_id)
            initial_data['id_escuela'] = escuela
        except Escuela.DoesNotExist:
            pass # La escuela no existe, el formulario se inicializará sin ella

    if request.method == 'POST':
        form = MaestroForm(request.POST, request=request)
        if form.is_valid():
            maestro = form.save(commit=False)
            maestro.save()
            messages.success(request, 'Maestro agregado correctamente.')
            # Redirigir de vuelta al detalle de la escuela si se agregó desde allí
            if escuela_id:
                return redirect('detalle_escuela', pk=escuela_id)
            return redirect('lista_maestros')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = MaestroForm(initial=initial_data, request=request)
    return render(request, 'gestion_escolar/form_maestro.html', {
        'form': form,
        'titulo': 'Agregar Maestro',
        'all_escuelas': all_escuelas
    })

@login_required
def editar_maestro(request, pk):
    maestro = get_object_or_404(Maestro, id_maestro=pk)
    documentos = maestro.documentos_expediente.all()
    
    if request.method == 'POST':
        # Distinguir si se está subiendo un documento o guardando el maestro
        if 'submit_documento' in request.POST:
            doc_form = DocumentoExpedienteForm(request.POST, request.FILES)
            if doc_form.is_valid():
                documento = doc_form.save(commit=False)
                documento.maestro = maestro
                documento.subido_por = request.user
                documento.save()
                messages.success(request, 'Documento subido correctamente.')
                return redirect('editar_maestro', pk=maestro.id_maestro)
            else:
                messages.error(request, 'Error al subir el documento.')
            # Si el formulario de documento falla, necesitamos el formulario principal para renderizar la página
            form = MaestroForm(instance=maestro, request=request)
        else:
            form = MaestroForm(request.POST, instance=maestro, request=request)
            if form.is_valid():
                form.save()
                messages.success(request, 'Maestro actualizado correctamente.')
                return redirect('lista_maestros')
            else:
                messages.error(request, 'Por favor corrige los errores.')
            # Si el formulario principal falla, necesitamos el formulario de documento vacío
            doc_form = DocumentoExpedienteForm()
    else:
        form = MaestroForm(instance=maestro, request=request)
        doc_form = DocumentoExpedienteForm()

    context = {
        'form': form,
        'doc_form': doc_form,
        'maestro': maestro,
        'documentos': documentos,
        'titulo': 'Editar Maestro'
    }
    return render(request, 'gestion_escolar/form_maestro.html', context)

def eliminar_maestro(request, pk):
    maestro = get_object_or_404(Maestro, id_maestro=pk)
    if request.method == 'POST':
        maestro.delete()
        messages.success(request, 'Maestro eliminado correctamente.')
        return redirect('lista_maestros')
    return render(request, 'gestion_escolar/eliminar_maestro.html', {'maestro': maestro})

def detalle_maestro(request, pk):
    maestro = get_object_or_404(Maestro, id_maestro=pk)
    documentos = maestro.documentos_expediente.all()
    
    if request.method == 'POST':
        form = DocumentoExpedienteForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.maestro = maestro
            documento.subido_por = request.user
            documento.save()
            messages.success(request, 'Documento subido correctamente.')
            return redirect('detalle_maestro', pk=maestro.id_maestro)
        else:
            messages.error(request, 'Error al subir el documento. Por favor, revise el formulario.')
    else:
        form = DocumentoExpedienteForm()

    context = {
        'maestro': maestro,
        'documentos': documentos,
        'form': form,
        'titulo': 'Detalle del Personal'
    }
    return render(request, 'gestion_escolar/detalle_maestro.html', context)

@login_required
def eliminar_documento_expediente(request, doc_pk):
    documento = get_object_or_404(DocumentoExpediente, pk=doc_pk)
    maestro_id = documento.maestro.id_maestro

    if request.method == 'POST':
        try:
            # Delete the file from storage
            documento.archivo.delete(save=False)
            # Delete the model instance
            documento.delete()
            messages.success(request, 'Documento eliminado correctamente.')
            return redirect('detalle_maestro', pk=maestro_id)
        except Exception as e:
            messages.error(request, f'Error al eliminar el documento: {e}')
            return redirect('detalle_maestro', pk=maestro_id)

    context = {
        'documento': documento,
        'maestro': documento.maestro,
    }
    return render(request, 'gestion_escolar/eliminar_documento_expediente.html', context)

# Vistas para diferentes funciones
def lista_por_funcion(request, funcion):
    # Mapeo de términos de búsqueda a nombres para mostrar y sus posibles valores en la BD
    funcion_mapping = {
        'DIRECTOR': {'display': 'Director', 'values': ['DIRECTOR', 'DIRECTOR (A)']},
        'SUPERVISOR': {'display': 'Supervisor', 'values': ['SUPERVISOR', 'SUPERVISOR (A)', 'SUPERVISOR(A)']},
        'MAESTRO_GRUPO': {'display': 'Maestro de Grupo', 'values': ['MAESTRO_GRUPO', 'MAESTRO(A) DE GRUPO', 'MAESTRO(A) DE GRUPO CON ESPECIALIDAD', 'MAESTRO(A) DE GRUPO ESPECIALISTA','MATRO(A) DE GRUPO ESPECIALISTA']},
        'DOCENTE_APOYO': {'display': 'Docente de Apoyo', 'values': ['MAESTRO(A) DE APOYO']},
        'PSICOLOGO': {'display': 'Psicólogo', 'values': ['PSICOLOGO', 'PSICÓLOGO(A)', 'PSICÓLOGO (A)']},
        'TRABAJADOR_SOCIAL': {'display': 'Trabajador Social', 'values': ['TRABAJADOR_SOCIAL', 'TRABAJADOR (A) SOCIAL']},
        'NIÑERO': {'display': 'Niñero', 'values': ['NIÑERO', 'NIÑERO(A)']},
        'SECRETARIO': {'display': 'Secretario', 'values': ['SECRETARIO', 'SECRETARIA ', 'SECRETARIO(A)']},
        'INTENDENTE': {'display': 'Intendente', 'values': ['INTENDENTE']},
        'VELADOR': {'display': 'Velador', 'values': ['VELADOR']},
        'VIGILANTE': {'display': 'Vigilante', 'values': ['VIGILANTE', 'VIGILANTE ']},
        'OTRO': {'display': 'Otro', 'values': ['OTRO']},
        'APOYO_TECNICO_PEDAGOGICO': {'display': 'Apoyo Técnico Pedagógico', 'values': ['APOYO TECNICO PEDAGOGICO']},
        'INSTRUCTOR_TALLER': {'display': 'Instructor de Taller', 'values': ['INSTRUCTOR(A) DE TALLER']},
        'MAESTRO_TALLER': {'display': 'Maestro de Taller', 'values': ['MAESTRO(A) DE TALLER', 'MAESTRO DE TALLER']},
        'MAESTRO_MUSICA': {'display': 'Maestro de Música', 'values': ['MAESTRO(A) MUSICA']},
        'MAESTRO_EDUCACION_FISICA': {'display': 'Maestro de Educación Física', 'values': ['MAESTRO(A) DE EDUCACIÓN FÍSICA']},
        'MEDICO': {'display': 'Médico', 'values': ['MÉDICO(A)', 'MÉDICO (A)']},
        'PROMOTOR_TIC': {'display': 'Promotor TIC', 'values': ['PROMOTOR TIC', 'PROMOTOR TIC ']},
        'TERAPISTA_FISICO': {'display': 'Terapista Físico', 'values': ['TERAPISTA FISICO ']},
        'BIBLIOTECARIO': {'display': 'Bibliotecario', 'values': ['BIBLIOTECARIO(A)']},
        'ADMINISTRATIVO_ESPECIALIZADO': {'display': 'Administrativo Especializado', 'values': ['ADMINISTRATIVO ESPECIALIZADO']},
        'OFICIAL_SERVICIOS_MANTENIMIENTO': {'display': 'Oficial de Servicios y Mantenimiento', 'values': ['OFICIAL DE SERVICIOS Y MANTENIMIENTO', 'OFICIAL DE SERVICIOS DE MANTENIMIENTO']},
        'ASISTENTE_DE_SERVICIOS': {'display': 'Asistente de Servicios', 'values': ['ASISTENTE DE SERVICIOS']},
        'ASESOR_JURIDICO': {'display': 'Asesor Jurídico', 'values': ['ASESOR JURÍDICO']},
        'AUXILIAR_DE_GRUPO': {'display': 'Auxiliar de Grupo', 'values': ['AUXILIAR DE GRUPO']},
        'MAESTRO_COMUNICACION': {'display': 'Maestro de Comunicación', 'values': ['MAESTRO(A) DE COMUNICACIÓN ']},
        'MAESTRO_AULA_HOSPITALARIA': {'display': 'Maestro Aula Hospitalaria', 'values': ['MAESTRO(A) AULA HOSPITALARIA']},
    }

    # Obtener los valores de función a buscar
    funcion_info = funcion_mapping.get(funcion)
    if not funcion_info:
        # Si la función no está en el mapeo, intentar con el nombre tal cual
        funcion_values = [funcion]
        funcion_display = funcion.replace(' ', '_').title()
    else:
        funcion_values = funcion_info['values']
        funcion_display = funcion_info['display']

    print(f"DEBUG: Buscando maestros con funcion__in: {funcion_values}")

    trabajadores = Maestro.objects.filter(
        funcion__in=funcion_values
    ).exclude(
        id_maestro__isnull=True
    ).exclude(
        id_maestro=''
    ).order_by('a_paterno', 'a_materno', 'nombres')

    print(f"DEBUG: Se encontraron {trabajadores.count()} maestros.")

    return render(request, 'gestion_escolar/lista_por_funcion.html', {
        'trabajadores': trabajadores,
        'funcion': funcion,
        'funcion_display': funcion_display,
        'titulo': f'{funcion_display}es' if funcion.endswith('OR') else f'{funcion_display}s'
    })

# Vistas específicas para cada función (opcional pero útil para URLs amigables)
def lista_directores(request):
    return lista_por_funcion(request, 'DIRECTOR')

def lista_supervisores_maestros(request):
    return lista_por_funcion(request, 'SUPERVISOR')

def lista_maestros_grupo(request):
    return lista_por_funcion(request, 'MAESTRO_GRUPO')

def lista_psicologos(request):
    return lista_por_funcion(request, 'PSICOLOGO')

def lista_trabajadores_sociales(request):
    return lista_por_funcion(request, 'TRABAJADOR_SOCIAL')

def lista_docentes_apoyo(request):
    return lista_por_funcion(request, 'DOCENTE_APOYO')

# Vistas para Trámites
def generar_tramites_generales(request):
    if request.user.groups.filter(name='Directores').exists():
        raise PermissionDenied
    if request.method == 'POST':
        form = TramiteForm(request.POST, form_type='tramites') # Pass form_type
        if form.is_valid():
            plantilla_id = form.cleaned_data['plantilla'].id
            plantilla_tramite = PlantillaTramite.objects.get(id=plantilla_id)

            success, message = generate_word_document(form.cleaned_data, plantilla_tramite)

            if success:
                # Crear registro en el historial
                try:
                    maestro_titular_obj = form.cleaned_data.get('maestro_titular')
                    print(f"DEBUG: Maestro Titular en generar_tramites_generales: {maestro_titular_obj}") # DEBUG LINE
                    Historial.objects.create(
                        usuario=request.user,
                        tipo_documento=f"Trámite - {plantilla_tramite.nombre}",
                        maestro=maestro_titular_obj,
                        ruta_archivo=message,
                        motivo=form.cleaned_data.get('motivo_tramite').motivo_tramite if form.cleaned_data.get('motivo_tramite') else '',
                        maestro_secundario_nombre=get_full_name(form.cleaned_data.get('maestro_interino')),
                        datos_tramite=serialize_form_data(form.cleaned_data)
                    )
                except Exception as e:
                    messages.warning(request, f"Advertencia: El trámite se generó pero no se pudo guardar en el historial: {e}")

                # Leer el archivo generado y enviarlo como respuesta para descarga
                with open(message, 'rb') as doc_file:
                    response = HttpResponse(doc_file.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(message)}"'
                    messages.success(request, 'Trámite generado y descargado correctamente.')
                    return response
            else:
                messages.error(request, f'Error al generar el trámite: {message}')
                return redirect('generar_tramites_generales') # Redirigir en caso de error
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = TramiteForm(form_type='tramites') # Pass form_type

    context = {
        'form': form,
        'titulo': 'Generar Trámite'
    }
    return render(request, 'gestion_escolar/generar_tramite.html', context)

def generar_oficios(request):
    if request.user.groups.filter(name='Directores').exists():
        raise PermissionDenied
    if request.method == 'POST':
        form = TramiteForm(request.POST, form_type='oficios') # Pass form_type
        if form.is_valid():
            plantilla_id = form.cleaned_data['plantilla'].id
            plantilla_tramite = PlantillaTramite.objects.get(id=plantilla_id)

            success, message = generate_word_document(form.cleaned_data, plantilla_tramite)

            if success:
                # Crear registro en el historial
                try:
                    Historial.objects.create(
                        usuario=request.user,
                        tipo_documento=f"Oficio - {plantilla_tramite.nombre}",
                        maestro=form.cleaned_data.get('maestro_titular'),
                        ruta_archivo=message,
                        motivo=form.cleaned_data.get('motivo_tramite').motivo_tramite if form.cleaned_data.get('motivo_tramite') else '',
                        maestro_secundario_nombre=get_full_name(form.cleaned_data.get('maestro_interino')),
                        datos_tramite=serialize_form_data(form.cleaned_data)
                    )
                except Exception as e:
                    messages.warning(request, f"Advertencia: El oficio se generó pero no se pudo guardar en el historial: {e}")

                # Leer el archivo generado y enviarlo como respuesta para descarga
                with open(message, 'rb') as doc_file:
                    response = HttpResponse(doc_file.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(message)}"'
                    messages.success(request, 'Oficio generado y descargado correctamente.')
                    return response
            else:
                messages.error(request, f'Error al generar el oficio: {message}')
                return redirect('generar_oficios') # Redirigir en caso de error
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = TramiteForm(form_type='oficios') # Pass form_type

    context = {
        'form': form,
        'titulo': 'Generar Oficio'
    }
    return render(request, 'gestion_escolar/generar_tramite.html', context)

def get_motivos_tramite_ajax(request):
    plantilla_id = request.GET.get('plantilla_id')
    motivos_filtrados = []

    if plantilla_id:
        try:
            plantilla = PlantillaTramite.objects.get(id=plantilla_id)
            opcion = plantilla.nombre.strip().upper() # Normalizar el nombre de la plantilla

            if opcion == "REINGRESO" or opcion == "FILIACION" or opcion == "SOLICITUD DE ASIGNACION" or opcion == "REINGRESO SIN PRELACION" or opcion == "JUSTIFICACION DE PERFIL" or opcion == "REPORTE DE VACANCIA":
                ids = [1, 2, 3, 4, 5, 6, 7, 21, 22, 24, 38]
            elif opcion == "CONSTANCIAS":
                ids = [20, 23, 29, 30, 31, 32, 33, 34, 35, 36, 37]
            elif opcion == "CAMBIO DEL CENTRO DE TRABAJO":
                ids = [19, 13]
            elif opcion == "CUADRO CAMBIOS CON FOLIO":
                ids = [13]
            elif opcion == "PROPUESTA DE MOVIMIENTO":
                ids = [11, 12, 25, 26, 27]
            elif opcion == "ALTA INICIAL": # Nuevo tipo de trámite
                ids = [39]
            elif opcion == "OFICIO DE REINCORPORACION":
                ids = [1, 2, 4, 15, 21, 22, 24]
            else:
                ids = []

            if ids:
                motivos_filtrados_qs = MotivoTramite.objects.filter(id__in=ids).order_by('motivo_tramite')
            else:
                motivos_filtrados_qs = MotivoTramite.objects.all().order_by('motivo_tramite')

            for motivo in motivos_filtrados_qs:
                motivos_filtrados.append({'id': motivo.id, 'text': motivo.motivo_tramite})

        except PlantillaTramite.DoesNotExist:
            pass

    return JsonResponse(motivos_filtrados, safe=False)

@login_required
def buscar_maestros_ajax(request):
    search_term = request.GET.get('term', '')
    
    # Dividir el término de búsqueda por espacios
    terms = [term for term in search_term.split() if term]
    
    # Iniciar una consulta vacía
    query = Q()
    
    # Construir una consulta que busque cada término en los campos de nombre
    for term in terms:
        query &= (
            Q(nombres__icontains=term) |
            Q(a_paterno__icontains=term) |
            Q(a_materno__icontains=term)
        )
    
    # Filtrar maestros que coincidan con todos los términos de búsqueda
    maestros = Maestro.objects.filter(query).order_by('a_paterno', 'a_materno', 'nombres')[:20] # Limitar a 20 resultados

    results = []
    for maestro in maestros:
        full_name = f"{maestro.a_paterno or ''} {maestro.a_materno or ''} {maestro.nombres or ''}".strip()
        results.append({
            "id": maestro.id_maestro,
            "text": full_name
        })

    return JsonResponse({'results': results})

@login_required
def get_maestro_data_ajax(request):
    maestro_id = request.GET.get('maestro_id')

    data = {}
    if maestro_id:
        try:
            maestro = Maestro.objects.get(id_maestro=maestro_id)
            data = {
                'curp': maestro.curp or '',
                'rfc': maestro.rfc or '',
                'clave_presupuestal': maestro.clave_presupuestal or '',
                'categoria': maestro.categog.descripcion if maestro.categog else '',
                'funcion': maestro.funcion or '',
            }
        except Maestro.DoesNotExist:
            data = {'error': 'Maestro no encontrado'}
    return JsonResponse(data)

# Vistas para Categorías
def lista_categorias(request):
    if request.user.groups.filter(name='Directores').exists():
        raise PermissionDenied
    query = request.GET.get('q')
    categorias = Categoria.objects.all().order_by('id_categoria')

    if query:
        categorias = categorias.filter(
            Q(id_categoria__icontains=query) | Q(descripcion__icontains=query)
        )

    context = {
        'categorias': categorias,
        'query': query,
    }
    return render(request, 'gestion_escolar/lista_categorias.html', context)

def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada correctamente.')
            return redirect('lista_categorias')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = CategoriaForm(instance=categoria)
    return render(request, 'gestion_escolar/form_categoria.html', {'form': form, 'titulo': 'Editar Categoría'})

def eliminar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoría eliminada correctamente.')
        return redirect('lista_categorias')
    return render(request, 'gestion_escolar/eliminar_categoria.html', {'categoria': categoria})

from django.http import JsonResponse, HttpResponse, FileResponse, HttpResponseForbidden

@login_required
def historial(request):
    if request.user.groups.filter(name='Directores').exists():
        raise PermissionDenied
    historial_items = Historial.objects.select_related('usuario', 'maestro').all()
    context = {
        'historial_items': historial_items,
        'titulo': 'Historial de Documentos'
    }
    return render(request, 'gestion_escolar/historial.html', context)

@login_required
def historial_detalle_lote(request, historial_id):
    historial_item = get_object_or_404(Historial, id=historial_id)
    if historial_item.lote_reporte:
        lote = historial_item.lote_reporte
        vacancias = lote.vacancias.all()
        context = {
            'historial_item': historial_item,
            'lote': lote,
            'vacancias': vacancias,
            'titulo': f'Detalle de Reporte de Vacancia (Lote {lote.id})'
        }
        return render(request, 'gestion_escolar/historial_detalle_lote.html', context)
    else:
        messages.error(request, "Este registro de historial no está asociado a un lote de vacancia.")
        return redirect('historial')

@login_required
def historial_detalle_tramite(request, historial_id):
    historial_item = get_object_or_404(Historial, id=historial_id)
    if historial_item.datos_tramite:
        context = {
            'historial_item': historial_item,
            'datos_tramite': historial_item.datos_tramite,
            'titulo': f'Detalle de {historial_item.tipo_documento}'
        }
        return render(request, 'gestion_escolar/historial_detalle_tramite.html', context)
    else:
        messages.error(request, "Este registro de historial no contiene datos de trámite/oficio.")
        return redirect('historial')

@login_required
def descargar_archivo_historial(request, item_id):
    item = get_object_or_404(Historial, id=item_id)
    
    # Security check to prevent directory traversal
    if not os.path.abspath(item.ruta_archivo).startswith(os.path.abspath(settings.BASE_DIR)):
        messages.error(request, "Acceso denegado.")
        return redirect('historial')

    if os.path.exists(item.ruta_archivo):
        try:
            return FileResponse(open(item.ruta_archivo, 'rb'), as_attachment=True, filename=os.path.basename(item.ruta_archivo))
        except Exception as e:
            messages.error(request, f"No se pudo abrir el archivo: {e}")
            return redirect('historial')
    else:
        messages.error(request, "El archivo no fue encontrado en el servidor.")
        return redirect('historial')

@login_required
def eliminar_historial_item(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(Historial, id=item_id)
        try:
            # Opcional: Eliminar el archivo físico del servidor.
            # Por seguridad, esta línea está comentada.
            # if item.ruta_archivo and os.path.exists(item.ruta_archivo):
            #     os.remove(item.ruta_archivo)
            
            item.delete()
            return JsonResponse({'status': 'success', 'message': 'Registro eliminado correctamente.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)

@login_required
def guardar_observacion_historial(request, item_id):
    if request.method == 'POST':
        item = get_object_or_404(Historial, id=item_id)
        try:
            data = json.loads(request.body)
            item.observaciones = data.get('observaciones', '')
            item.save()
            return JsonResponse({'status': 'success', 'message': 'Observación guardada.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"¡Bienvenido, {username}!")
                return redirect('index') # Redirect to dashboard or a 'next' parameter
            else:
                messages.error(request, "Nombre de usuario o contraseña incorrectos.")
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = AuthenticationForm()
    
    context = {
        'form': form,
        'titulo': 'Iniciar Sesión'
    }
    return render(request, 'gestion_escolar/login.html', context)

def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('login') # Redirect to login page

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'¡Cuenta creada para {username}! Tu solicitud ha sido enviada para aprobación.')
            return redirect('login')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = SignUpForm()
    context = {
        'form': form,
        'titulo': 'Solicitud de Registro'
    }
    return render(request, 'gestion_escolar/signup.html', context)

@login_required
def export_maestro_csv(request, pk):
    maestro = get_object_or_404(Maestro, id_maestro=pk)
    
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="detalle_{maestro.a_paterno}_{maestro.id_maestro}.csv"'},
    )
    response.write('\ufeff') # BOM for Excel to handle UTF-8 correctly

    writer = csv.writer(response)

    # Define headers and data
    data = {
        "ID Maestro": maestro.id_maestro,
        "Nombre Completo": f'{maestro.nombres} {maestro.a_paterno} {maestro.a_materno}',
        "CURP": maestro.curp,
        "RFC": maestro.rfc,
        "Sexo": maestro.get_sexo_display(),
        "Estado Civil": maestro.get_est_civil_display(),
        "Fecha de Nacimiento": maestro.fecha_nacimiento,
        "Techo Financiero": maestro.techo_f,
        "C.C.T.": maestro.id_escuela.id_escuela if maestro.id_escuela else 'N/A',
        "Nombre del Centro de Trabajo": maestro.id_escuela.nombre_ct if maestro.id_escuela else 'N/A',
        "Zona Escolar": maestro.id_escuela.zona_esc.numero if maestro.id_escuela and maestro.id_escuela.zona_esc else 'N/A',
        "Clave Presupuestal": maestro.clave_presupuestal,
        "Categoría": maestro.categog,
        "Código": maestro.codigo,
        "Fecha de Ingreso": maestro.fecha_ingreso,
        "Fecha de Promoción": maestro.fecha_promocion,
        "Formación Académica": maestro.form_academica,
        "Horario": maestro.horario,
        "Función": maestro.get_funcion_display(),
        "Nivel de Estudio": maestro.get_nivel_estudio_display(),
        "Domicilio Particular": maestro.domicilio_part,
        "Población": maestro.poblacion,
        "Código Postal": maestro.codigo_postal,
        "Teléfono": maestro.telefono,
        "Email": maestro.email,
        "Status": maestro.get_status_display(),
        "Observaciones": maestro.observaciones,
    }

    # Write header row
    writer.writerow(data.keys())
    # Write data row
    writer.writerow(data.values())

    return response

@login_required
def exportar_maestros_excel(request):
    filtro = request.GET.get('filtro', '')
    print(f"DEBUG: Filtro recibido en exportar_maestros_excel: '{filtro}'")
    
    # Construir la consulta base con select_related para optimizar
    maestros_qs = Maestro.objects.select_related('id_escuela', 'id_escuela__zona_esc', 'categog').all().order_by('a_paterno', 'a_materno', 'nombres')

    # Aplicar filtro si existe
    if filtro:
        maestros_qs = maestros_qs.filter(
            Q(nombres__icontains=filtro) |
            Q(a_paterno__icontains=filtro) |
            Q(a_materno__icontains=filtro) |
            Q(rfc__icontains=filtro) |
            Q(curp__icontains=filtro) |
            Q(id_maestro__icontains=filtro) |
            Q(id_escuela__nombre_ct__icontains=filtro) |
            Q(id_escuela__id_escuela__icontains=filtro) |
            Q(categog__descripcion__icontains=filtro)
        )

    # Crear el libro de Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Maestros"

    # Definir los encabezados
    headers = [
        "ID Maestro", "Nombre(s)", "Apellido Paterno", "Apellido Materno", "RFC", "CURP",
        "Sexo", "Estado Civil", "Fecha Nacimiento", "Techo Financiero",
        "CCT", "Nombre del CT", "Zona Escolar", "Función", "Categoría",
        "Clave Presupuestal", "Código", "Fecha Ingreso", "Fecha Promoción",
        "Formación Académica", "Horario", "Nivel de Estudio", "Domicilio Particular",
        "Población", "Código Postal", "Teléfono", "Email", "Status", "Observaciones"
    ]
    ws.append(headers)

    # Escribir los datos de cada maestro
    for maestro in maestros_qs:
        escuela = maestro.id_escuela
        zona_numero = ''
        if escuela and escuela.zona_esc:
            zona_numero = escuela.zona_esc.numero

        row = [
            maestro.id_maestro,
            maestro.nombres,
            maestro.a_paterno,
            maestro.a_materno,
            maestro.rfc,
            maestro.curp,
            maestro.get_sexo_display(),
            maestro.get_est_civil_display(),
            maestro.fecha_nacimiento.strftime("%Y-%m-%d") if maestro.fecha_nacimiento else '',
            maestro.techo_f,
            escuela.id_escuela if escuela else '',
            escuela.nombre_ct if escuela else '',
            zona_numero,
            maestro.get_funcion_display(),
            maestro.categog.descripcion if maestro.categog else '',
            maestro.clave_presupuestal,
            maestro.codigo,
            maestro.fecha_ingreso.strftime("%Y-%m-%d") if maestro.fecha_ingreso else '',
            maestro.fecha_promocion.strftime("%Y-%m-%d") if maestro.fecha_promocion else '',
            maestro.form_academica,
            maestro.horario,
            maestro.get_nivel_estudio_display(),
            maestro.domicilio_part,
            maestro.poblacion,
            maestro.codigo_postal,
            maestro.telefono,
            maestro.email,
            maestro.get_status_display(),
            maestro.observaciones,
        ]
        ws.append(row)

    # Preparar la respuesta para la descarga
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="reporte_maestros.xlsx"'},
    )
    wb.save(response)

    return response

@login_required
def gestionar_lote_vacancia(request):
    if request.user.groups.filter(name='Directores').exists():
        raise PermissionDenied
    # Busca un lote en proceso para el usuario actual o crea uno nuevo
    # Primero, intenta obtener un lote existente
    lotes_en_proceso = LoteReporteVacancia.objects.filter(
        usuario_generador=request.user,
        estado='EN_PROCESO'
    ).order_by('-fecha_creacion')

    if lotes_en_proceso.exists():
        lote = lotes_en_proceso.first()
        # Si hay más de uno, marcar los demás como cancelados o eliminarlos
        if lotes_en_proceso.count() > 1:
            for old_lote in lotes_en_proceso[1:]:
                old_lote.estado = 'CANCELADO' # O eliminar: old_lote.delete()
                old_lote.save()
    else:
        lote = LoteReporteVacancia.objects.create(
            usuario_generador=request.user,
            estado='EN_PROCESO'
        )

    if request.method == 'POST':
        form = VacanciaForm(request.POST)
        if form.is_valid():
            # El formulario es válido, pero aún no guardamos la vacancia.
            # Primero, necesitamos calcular todos los campos derivados.
            maestro = form.cleaned_data['maestro_titular']
            escuela = maestro.id_escuela

            # Iniciar la creación de la instancia de Vacancia
            vacancia = form.save(commit=False)
            vacancia.lote = lote

            # Manejar Maestro Interino
            maestro_interino_obj = form.cleaned_data.get('maestro_interino')
            if maestro_interino_obj:
                vacancia.nombre_interino = f'{maestro_interino_obj.nombres} {maestro_interino_obj.a_paterno} {maestro_interino_obj.a_materno}'
                vacancia.curp_interino = maestro_interino_obj.curp

                # Obtener datos de prelación si existen
                if maestro_interino_obj.curp:
                    prelacion = Prelacion.objects.filter(curp=maestro_interino_obj.curp).first()
                    if prelacion:
                        vacancia.posicion_orden = prelacion.pos_orden
                        vacancia.folio_prelacion = prelacion.folio
            else:
                # Si no se selecciona un maestro interino, se usan los campos manuales del formulario
                vacancia.nombre_interino = form.cleaned_data.get('nombre_interino')
                vacancia.curp_interino = form.cleaned_data.get('curp_interino')
                # Si no hay maestro interino seleccionado, los campos de prelación manuales también deben ser considerados
                vacancia.posicion_orden = form.cleaned_data.get('posicion_orden_display') # Asumiendo que estos campos se llenan manualmente si no hay interino
                vacancia.folio_prelacion = form.cleaned_data.get('folio_prelacion_display') # Asumiendo que estos campos se llenan manualmente si no hay interino

            # --- Lógica de Transformación (portada de VBA) ---
            # 1. Dirección
            vacancia.direccion = f"{escuela.nombre_ct}, {escuela.domicilio}, DURANGO, {escuela.region}, {escuela.get_turno_display()}, ZONA ECONOMICA:{escuela.zona_economica}"

            # 2. Destino
            apreciacion_desc = form.cleaned_data['apreciacion'].descripcion
            if apreciacion_desc.startswith("ADMISIÓN"):
                vacancia.destino = "Admisión"
            elif apreciacion_desc.startswith("PROMOCIÓN"):
                vacancia.destino = "Promoción vertical"
            else:
                vacancia.destino = ""

            # 3. Sostenimiento y Turno
            vacancia.sostenimiento = "Federalizado" if escuela.sostenimiento == 'FEDERAL' else "Estatal"
            vacancia.turno = escuela.get_turno_display()

            # 4. Tipo de Movimiento para Reporte
            vacancia.tipo_movimiento_reporte = form.cleaned_data['tipo_movimiento_original']

            # 5. Tipo Plaza y Horas
            hrs = maestro.hrs or "00.0"
            vacancia.tipo_plaza = "JORNADA" if hrs == "00.0" else "HORA/SEMANA/MES"
            if hrs == "00.0":
                vacancia.horas = None
            else:
                try:
                    # Convertir a int para eliminar ceros iniciales y luego a str
                    vacancia.horas = str(int(float(hrs)))
                except (ValueError, TypeError):
                    vacancia.horas = None # En caso de que hrs no sea un número válido

            # 6. Otros campos directos del maestro o escuela
            vacancia.municipio = escuela.region
            vacancia.zona_economica = f"Zona {escuela.zona_economica}"
            vacancia.categoria = maestro.categog.id_categoria if maestro.categog else ''
            vacancia.clave_presupuestal = maestro.clave_presupuestal
            vacancia.techo_financiero = maestro.techo_f
            vacancia.clave_ct = escuela.id_escuela
            vacancia.nombre_titular_reporte = f'{maestro.nombres} {maestro.a_paterno} {maestro.a_materno}'

            vacancia.save()
            messages.success(request, "Vacancia agregada al lote actual.")
            return redirect('gestionar_lote_vacancia')
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = VacanciaForm()

    vacancias_en_lote = Vacancia.objects.filter(lote=lote).order_by('-id')
    context = {
        'form': form,
        'lote': lote,
        'vacancias_en_lote': vacancias_en_lote,
        'titulo': 'Generar Reporte de Vacancia'
    }
    return render(request, 'gestion_escolar/gestionar_lote_vacancia.html', context)

@login_required
def exportar_lote_vacancia(request, lote_id):
    lote = get_object_or_404(LoteReporteVacancia, id=lote_id, usuario_generador=request.user)
    vacancias = lote.vacancias.all()

    if not vacancias.exists():
        messages.error(request, "No hay vacancias en este lote para exportar.")
        return redirect('gestionar_lote_vacancia')

    template_path = os.path.join(settings.BASE_DIR, 'gestion_escolar', 'templates', 'tramites', 'Plantillas', 'Excel', 'FORMATOVACANCIAUSICAMM.xlsx')
    workbook = openpyxl.load_workbook(template_path)
    sheet = workbook.active

    # Fila inicial para escribir los datos
    row_num = 2

    # Campos en el orden del Excel
    campos_excel = [
        'nivel', 'entidad', 'municipio', 'direccion', 'region', 'zona_economica', 'destino', 'apreciacion',
        'tipo_vacante', 'tipo_plaza', 'horas', 'sostenimiento', 'fecha_inicio', 'fecha_final', 'categoria',
        'pseudoplaza', 'clave_presupuestal', 'techo_financiero', 'clave_ct', 'turno', 'tipo_movimiento_reporte', 'observaciones',
        'posicion_orden', 'folio_prelacion', 'curp_interino', 'nombre_interino'
    ]

    for vacancia in vacancias:
        for i, field_name in enumerate(campos_excel):
            cell = sheet.cell(row=row_num, column=i + 1)
            valor = getattr(vacancia, field_name, '')
            
            # Transformación específica para zona_economica (Romanos a Arábigos)
            if field_name == 'zona_economica' and isinstance(valor, str):
                valor = valor.replace('Zona II', 'Zona 2').replace('Zona III', 'Zona 3')

            # Si el campo es una FK, obtener su representación de texto
            if hasattr(valor, 'descripcion'):
                valor = valor.descripcion
            cell.value = valor
        row_num += 1

    # Guardar el archivo en el servidor
    output_dir = os.path.join(settings.BASE_DIR, 'reportes_vacancias')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"VACANCIA_{timestamp}.xlsx"
    output_path_server = os.path.join(output_dir, output_filename)
    workbook.save(output_path_server)

    # Crear registro en el historial
    try:
        Historial.objects.create(
            usuario=request.user,
            tipo_documento="Reporte de Vacancia",
            maestro=None,  # No se asocia a un único maestro
            ruta_archivo=output_path_server,
            motivo="Reporte de Vacancia",
            lote_reporte=lote
        )
    except Exception as e:
        messages.warning(request, f"Advertencia: El reporte se generó pero no se pudo guardar en el historial: {e}")

    # Actualizar el campo archivo_generado del lote
    lote.archivo_generado = os.path.join('reportes_vacancias', output_filename) # Guardar la ruta relativa
    lote.save() # Guardar el lote para persistir la ruta del archivo

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={output_filename}'
    workbook.save(response)

    # Marcar el lote como generado y limpiar vacancias (o mantener para historial)
    lote.estado = 'GENERADO'
    lote.fecha_generado = datetime.now()
    lote.save()

    # Crear un nuevo lote en proceso para el usuario
    LoteReporteVacancia.objects.create(usuario_generador=request.user, estado='EN_PROCESO')

    # Opcional: Crear un nuevo lote en proceso para el usuario
    LoteReporteVacancia.objects.create(usuario_generador=request.user, estado='EN_PROCESO')

    return response

@login_required
def get_maestro_data_for_vacancia(request):
    maestro_id = request.GET.get('maestro_id')
    data = {}
    if maestro_id:
        try:
            maestro = Maestro.objects.get(id_maestro=maestro_id)
            data = {
                'nombre_completo': f'{maestro.nombres} {maestro.a_paterno} {maestro.a_materno}',
                'clave_presupuestal': maestro.clave_presupuestal
            }
        except Maestro.DoesNotExist:
            data = {'error': 'Maestro no encontrado'}
    return JsonResponse(data)

@login_required
def get_interino_and_prelacion_data_ajax(request):
    maestro_id = request.GET.get('maestro_id')
    data = {
        'curp_interino': '',
        'folio_prelacion': '',
        'posicion_orden': '',
        'tipo_val': '',
        'error': ''
    }

    if maestro_id:
        try:
            maestro = Maestro.objects.get(id_maestro=maestro_id)
            data['curp_interino'] = maestro.curp or '' # Siempre devolver la CURP si el maestro existe

            # Buscar en la tabla Prelacion usando la CURP del interino
            if maestro.curp:
                prelacion = Prelacion.objects.filter(curp=maestro.curp).first()
                if prelacion:
                    data['folio_prelacion'] = prelacion.folio or ''
                    data['posicion_orden'] = prelacion.pos_orden or ''
                    data['tipo_val'] = prelacion.tipo_val or ''
                # else: No establecer data['error'] aquí, solo significa que no hay datos de prelación
            # else: No establecer data['error'] aquí, solo significa que el maestro no tiene CURP registrada, pero el maestro sí existe

        except Maestro.DoesNotExist:
            data['error'] = 'Maestro interino no encontrado.'
            data['curp_interino'] = 'N/A' # Asegurarse de que la CURP también refleje el error
        except Exception as e:
            data['error'] = f'Error inesperado: {str(e)}'
            data['curp_interino'] = 'Error' # Asegurarse de que la CURP también refleje el error

    return JsonResponse(data)

@login_required
def eliminar_vacancia_lote(request, pk):
    if request.method == 'POST':
        vacancia = get_object_or_404(Vacancia, pk=pk)
        # Asegurarse de que la vacancia pertenece al lote en proceso del usuario actual
        if vacancia.lote.usuario_generador == request.user and vacancia.lote.estado == 'EN_PROCESO':
            vacancia.delete()
            messages.success(request, "Vacancia eliminada del lote correctamente.")
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': 'No autorizado para eliminar esta vacancia.'}, status=403)
    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)

# --- VISTAS PARA PENDIENTES ---

class PendienteCreateView(LoginRequiredMixin, CreateView):
    form_class = PendienteForm
    template_name = 'gestion_escolar/pendiente_form.html'
    success_url = reverse_lazy('pendientes_activos')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, "Pendiente creado correctamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nuevo Pendiente'
        return context

class PendienteActiveListView(LoginRequiredMixin, ListView):
    model = Pendiente
    template_name = 'gestion_escolar/pendiente_list.html'
    context_object_name = 'pendientes'

    def get_queryset(self):
        today = timezone.now().date()
        return Pendiente.objects.filter(
            usuario=self.request.user,
            completado=False,
            fecha_programada__lte=today
        ).order_by('fecha_programada')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Mis Pendientes Activos'
        context['vista_todos'] = False
        return context

class PendienteAllListView(LoginRequiredMixin, ListView):
    model = Pendiente
    template_name = 'gestion_escolar/pendiente_list.html'
    context_object_name = 'pendientes'

    def get_queryset(self):
        return Pendiente.objects.filter(usuario=self.request.user).order_by('-fecha_programada')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Todos Mis Pendientes'
        context['vista_todos'] = True
        return context

@login_required
def pendiente_marcar_completado(request, pk):
    if request.method == 'POST':
        pendiente = get_object_or_404(Pendiente, pk=pk, usuario=request.user)
        pendiente.completado = True
        pendiente.save()
        messages.success(request, f"El pendiente '{pendiente.titulo}' ha sido marcado como completado.")
        return redirect('pendientes_activos')
    else:
        return redirect('pendientes_activos')

# --- VISTAS PARA CORRESPONDENCIA ---

class CorrespondenciaInboxView(LoginRequiredMixin, ListView):
    model = Correspondencia
    template_name = 'gestion_escolar/correspondencia_inbox.html'
    context_object_name = 'mensajes'

    def get_queryset(self):
        return Correspondencia.objects.filter(destinatario=self.request.user).order_by('-fecha_creacion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Bandeja de Entrada'
        return context

class CorrespondenciaDetailView(LoginRequiredMixin, DetailView):
    model = Correspondencia
    template_name = 'gestion_escolar/correspondencia_detail.html'
    context_object_name = 'mensaje'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.destinatario == self.request.user:
            if not obj.leido:
                obj.leido = True
                obj.save()
            return obj
        else:
            raise PermissionDenied("No tienes permiso para ver este mensaje.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = self.object.asunto
        return context

@login_required
def correspondencia_eliminar(request, pk):
    if request.method == 'POST':
        mensaje = get_object_or_404(Correspondencia, pk=pk)
        if mensaje.destinatario == request.user:
            mensaje.delete()
            messages.success(request, "Mensaje eliminado correctamente.")
        else:
            messages.error(request, "No tienes permiso para eliminar este mensaje.")
    return redirect('correspondencia_inbox')


class CorrespondenciaCreateView(LoginRequiredMixin, CreateView):
    form_class = CorrespondenciaForm
    template_name = 'gestion_escolar/correspondencia_form.html'
    success_url = reverse_lazy('correspondencia_inbox')

    def form_valid(self, form):
        form.instance.remitente = self.request.user
        messages.success(self.request, "Mensaje enviado correctamente.")
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Excluir al usuario actual de la lista de destinatarios
        form.fields['destinatario'].queryset = User.objects.exclude(pk=self.request.user.pk)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Redactar Nuevo Mensaje'
        return context