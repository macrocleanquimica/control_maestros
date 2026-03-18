import json
import openpyxl
import datetime
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.db.models import Q, Count
from django.db.models.functions import Upper, Trim

from ..models import Maestro, Zona, Escuela, RegistroCorrespondencia # Import RegistroCorrespondencia

@permission_required('gestion_escolar.acceder_reportes', raise_exception=True)
def reportes_dashboard(request):
    ultimos_registros_correspondencia = []
    has_correspondencia_perm = request.user.has_perm('gestion_escolar.ver_ultima_correspondencia')
    print(f"DEBUG: User has 'ver_ultima_correspondencia' permission: {has_correspondencia_perm}")
    if has_correspondencia_perm:
        ultimos_registros_correspondencia = RegistroCorrespondencia.objects.all().order_by('-fecha_recibido', '-fecha_registro')[:5] # Get latest 5

    context = {
        'titulo': 'Dashboard de Reportes',
        'ultimos_registros_correspondencia': ultimos_registros_correspondencia,
    }
    return render(request, 'gestion_escolar/reportes_dashboard.html', context)

@login_required
def reporte_personal_fuera_adscripcion(request):
    personal_qs = Maestro.objects.annotate(
        techo_f_clean=Trim(Upper('techo_f')),
        id_escuela_clean=Trim(Upper('id_escuela__id_escuela'))
    ).exclude(techo_f__isnull=True).exclude(techo_f='')

    personal_fuera_adscripcion = [p for p in personal_qs if p.techo_f_clean != p.id_escuela_clean]

    context = {
        'personal_fuera_adscripcion': personal_fuera_adscripcion,
        'titulo': 'Reporte de Personal Fuera de Adscripción'
    }
    return render(request, 'gestion_escolar/reporte_fuera_adscripcion.html', context)

@login_required
def export_maestro_excel(request, pk):
    maestro = get_object_or_404(Maestro, id_maestro=pk)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Detalle_{maestro.id_maestro}"

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
        "Categoría": str(maestro.categog) if maestro.categog else '',
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

    for key, value in data.items():
        if isinstance(value, date):
            value = value.strftime("%d/%m/%Y")
        ws.append([key, value])

    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 50

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="detalle_{maestro.a_paterno}_{maestro.id_maestro}.xlsx"'},
    )
    wb.save(response)

    return response

@login_required
def exportar_maestros_excel(request):
    filtro = request.GET.get('filtro', '')
    funcion = request.GET.get('funcion', '')

    maestros_qs = Maestro.objects.select_related('id_escuela', 'id_escuela__zona_esc', 'categog').all().order_by('a_paterno', 'a_materno', 'nombres')

    if funcion:
        # This mapping should ideally be in a more centralized place
        funcion_mapping = {
            'DIRECTOR': {'values': ['DIRECTOR', 'DIRECTOR (A)']},
            # ... add all other mappings here ...
        }
        funcion_info = funcion_mapping.get(funcion)
        if funcion_info:
            maestros_qs = maestros_qs.filter(funcion__in=funcion_info['values'])

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

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Maestros"

    headers = [
        "ID Maestro", "Nombre(s)", "Apellido Paterno", "Apellido Materno", "RFC", "CURP",
        "Sexo", "Estado Civil", "Fecha Nacimiento", "Techo Financiero",
        "CCT", "Nombre del CT", "Zona Escolar", "Función", "Categoría",
        "Clave Presupuestal", "Código", "Fecha Ingreso", "Fecha Promoción",
        "Formación Académica", "Horario", "Nivel de Estudio", "Domicilio Particular",
        "Población", "Código Postal", "Teléfono", "Email", "Status", "Observaciones"
    ]
    ws.append(headers)

    for maestro in maestros_qs:
        escuela = maestro.id_escuela
        zona_numero = ''
        if escuela and escuela.zona_esc:
            zona_numero = escuela.zona_esc.numero

        row = [
            maestro.id_maestro, maestro.nombres, maestro.a_paterno, maestro.a_materno, maestro.rfc, maestro.curp,
            maestro.get_sexo_display(), maestro.get_est_civil_display(),
            maestro.fecha_nacimiento.strftime("%Y-%m-%d") if maestro.fecha_nacimiento else '',
            maestro.techo_f, escuela.id_escuela if escuela else '', escuela.nombre_ct if escuela else '', zona_numero,
            maestro.get_funcion_display(), maestro.categog.descripcion if maestro.categog else '',
            maestro.clave_presupuestal, maestro.codigo,
            maestro.fecha_ingreso.strftime("%Y-%m-%d") if maestro.fecha_ingreso else '',
            maestro.fecha_promocion.strftime("%Y-%m-%d") if maestro.fecha_promocion else '',
            maestro.form_academica, maestro.horario, maestro.get_nivel_estudio_display(),
            maestro.domicilio_part, maestro.poblacion, maestro.codigo_postal, maestro.telefono, maestro.email,
            maestro.get_status_display(), maestro.observaciones,
        ]
        ws.append(row)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="reporte_maestros.xlsx"'},
    )
    wb.save(response)

    return response

@login_required
def reporte_distribucion_funcion(request):
    maestros_qs = Maestro.objects.all()

    zona_id = request.GET.get('zona')
    escuela_id = request.GET.get('escuela')

    if zona_id:
        maestros_qs = maestros_qs.filter(id_escuela__zona_esc_id=zona_id)
    
    if escuela_id:
        maestros_qs = maestros_qs.filter(id_escuela_id=escuela_id)

    distribucion = maestros_qs.values('funcion').annotate(total=Count('funcion')).order_by('-total')

    labels = [d['funcion'] for d in distribucion]
    data = [d['total'] for d in distribucion]

    zonas = Zona.objects.all()
    escuelas = Escuela.objects.all()

    context = {
        'titulo': 'Distribución de Personal por Función',
        'labels': json.dumps(labels),
        'data': json.dumps(data),
        'zonas': zonas,
        'escuelas': escuelas,
        'selected_zona': int(zona_id) if zona_id else None,
        'selected_escuela': int(escuela_id) if escuela_id else None,
    }
    return render(request, 'gestion_escolar/reporte_distribucion_funcion.html', context)

@login_required
def export_personal_fuera_adscripcion_excel(request):
    """Exporta el reporte de personal fuera de adscripción a un archivo Excel, aplicando un filtro de búsqueda."""
    filtro = request.GET.get('filtro', '')

    # 1. Obtener el queryset base
    personal_qs = Maestro.objects.annotate(
        techo_f_clean=Trim(Upper('techo_f')),
        id_escuela_clean=Trim(Upper('id_escuela__id_escuela'))
    ).exclude(techo_f__isnull=True).exclude(techo_f='').select_related('id_escuela', 'id_escuela__zona_esc', 'categog')

    personal_fuera_adscripcion = [p for p in personal_qs if p.techo_f_clean != p.id_escuela_clean]
    
    # Convertir la lista de objetos a un queryset para poder filtrar más
    pks = [p.pk for p in personal_fuera_adscripcion]
    queryset = Maestro.objects.filter(pk__in=pks)

    # 2. Aplicar el filtro si existe
    if filtro:
        queryset = queryset.filter(
            Q(nombres__icontains=filtro) |
            Q(a_paterno__icontains=filtro) |
            Q(a_materno__icontains=filtro) |
            Q(clave_presupuestal__icontains=filtro) |
            Q(id_escuela__id_escuela__icontains=filtro) | # CCT Físico
            Q(techo_f__icontains=filtro) # CCT de Pago
        )

    # 3. Crear el libro de Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Personal Fuera de Adscripción"

    # 4. Definir los encabezados
    headers = [
        "ID Maestro", "Nombre(s)", "Apellido Paterno", "Apellido Materno", "RFC", "CURP",
        "Sexo", "Estado Civil", "Fecha Nacimiento", "Techo Financiero",
        "CCT Físico", "Nombre del CT Físico", "Zona Escolar", "Función", "Categoría",
        "Clave Presupuestal", "Código", "Fecha Ingreso", "Fecha Promoción",
        "Formación Académica", "Horario", "Nivel de Estudio", "Domicilio Particular",
        "Población", "Código Postal", "Teléfono", "Email", "Status", "Observaciones"
    ]
    ws.append(headers)

    # 5. Escribir los datos de cada maestro
    for maestro in queryset:
        escuela = maestro.id_escuela
        zona_numero = ''
        if escuela and escuela.zona_esc:
            zona_numero = escuela.zona_esc.numero

        row = [
            maestro.id_maestro, maestro.nombres, maestro.a_paterno, maestro.a_materno, maestro.rfc, maestro.curp,
            maestro.get_sexo_display(), maestro.get_est_civil_display(),
            maestro.fecha_nacimiento.strftime("%Y-%m-%d") if maestro.fecha_nacimiento else '',
            maestro.techo_f, 
            escuela.id_escuela if escuela else '', 
            escuela.nombre_ct if escuela else '', 
            zona_numero,
            maestro.get_funcion_display(), 
            maestro.categog.descripcion if maestro.categog else '',
            maestro.clave_presupuestal, maestro.codigo,
            maestro.fecha_ingreso.strftime("%Y-%m-%d") if maestro.fecha_ingreso else '',
            maestro.fecha_promocion.strftime("%Y-%m-%d") if maestro.fecha_promocion else '',
            maestro.form_academica, maestro.horario, maestro.get_nivel_estudio_display(),
            maestro.domicilio_part, maestro.poblacion, maestro.codigo_postal, maestro.telefono, maestro.email,
            maestro.get_status_display(), maestro.observaciones,
        ]
        ws.append(row)

    # 6. Preparar la respuesta para la descarga
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="reporte_personal_fuera_adscripcion.xlsx"'},
    )
    wb.save(response)

    return response

@login_required
def exportar_escuelas_excel(request):
    """Exporta el reporte de escuelas a un archivo Excel, aplicando un filtro de búsqueda."""
    filtro = request.GET.get('filtro', '')

    # 1. Obtener el queryset base
    escuelas_qs = Escuela.objects.select_related('zona_esc').all().order_by('id_escuela') # Ordenar por CCT

    # 2. Aplicar el filtro si existe
    if filtro:
        escuelas_qs = escuelas_qs.filter(
            Q(id_escuela__icontains=filtro) |
            Q(nombre_ct__icontains=filtro) |
            Q(zona_esc__numero__icontains=filtro) |
            Q(zona_economica__icontains=filtro) |
            Q(u_d__icontains=filtro) |
            Q(turno__icontains=filtro) |
            Q(sostenimiento__icontains=filtro)
        )

    # 3. Crear el libro de Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Escuelas"

    # 4. Definir los encabezados
    headers = [
        "CCT", "Nombre", "Zona", "Turno", "Zona Económica", 
        "U.D.", "Sostenimiento", "Domicilio", "Localidad", "Municipio"
    ]
    ws.append(headers)

    # 5. Escribir los datos de cada escuela
    for escuela in escuelas_qs:
        zona_numero = escuela.zona_esc.numero if escuela.zona_esc else ''
        
        row = [
            escuela.id_escuela,
            escuela.nombre_ct,
            zona_numero,
            escuela.get_turno_display(),
            escuela.zona_economica,
            escuela.u_d,
            escuela.get_sostenimiento_display(),
            escuela.domicilio,
            '', # Localidad no disponible en modelo
            ''  # Municipio no disponible en modelo
        ]
        ws.append(row)

    # 6. Ajustar ancho de columnas
    ws.column_dimensions['A'].width = 15 # CCT
    ws.column_dimensions['B'].width = 40 # Nombre
    ws.column_dimensions['H'].width = 30 # Domicilio

    # 7. Preparar la respuesta para la descarga
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="reporte_escuelas.xlsx"'},
    )
    wb.save(response)

    return response

@login_required
@permission_required('gestion_escolar.acceder_reportes', raise_exception=True)
def exportar_maestros_personalizado_excel(request):
    """
    Exporta el reporte 'BD de Horizontal' con 24 columnas en el orden solicitado.
    """
    maestros_qs = Maestro.objects.select_related(
        'id_escuela', 
        'id_escuela__zona_esc', 
        'categog'
    ).prefetch_related('incentivos').all().order_by('a_paterno', 'a_materno', 'nombres')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BD Horizontal"

    # Encabezados solicitados (24 columnas)
    headers = [
        "RFC", "CURP", "NOMBRE COMPLETO", "NIVEL EDUCATIVO", "CLAVE PRESUPUESTAL",
        "DESCRIPCION CATEGORIA", "FUNCION", "TECHO FINANCIERO", "C.C.T",
        "NOMBRE DEL C.C.T COMPLETO", "NOMBRE DEL CENTRO DE TRABAJO", "ZONA",
        "SEXO", "CÓDIGO", "FECHA DE INGRESO", "FORMACIÓN ACADEMICA",
        "SITUACIÓN", "FECHA DE PROMOCIÓN", "ESTADO CIVIL", "TELEFONO",
        "STATUS", "OBSERVACIONES", "SOSTENIMIENTO", "DESCRIPCION DEL CODIGO"
    ]
    ws.append(headers)

    # Mapeo de códigos
    codigo_map = {
        '10': 'BASE',
        '95': 'INTERINO LIMITADO',
        '96': 'INTERINO POR VACANTE DEFINITIVA',
        '09': 'PROVISIONAL',
        '20': 'HONORARIOS',
    }

    for maestro in maestros_qs:
        escuela = maestro.id_escuela
        zona_numero = escuela.zona_esc.numero if escuela and escuela.zona_esc else ''
        
        # Situación: 10 -> BASE, otros -> INTERINO
        situacion = "BASE" if maestro.codigo == '10' else "INTERINO"
        desc_codigo = codigo_map.get(maestro.codigo, "OTRO")

        row = [
            maestro.rfc or '',
            maestro.curp or '',
            f"{maestro.nombres or ''} {maestro.a_paterno or ''} {maestro.a_materno or ''}".strip().upper(),
            "EDUCACIÓN ESPECIAL",
            maestro.clave_presupuestal or '',
            maestro.categog.descripcion if maestro.categog else '',
            maestro.get_funcion_display() or '',
            maestro.techo_f or '',
            escuela.id_escuela if escuela else '',
            escuela.nombre_ct if escuela else '',
            escuela.nombre_ct if escuela else '',
            zona_numero,
            maestro.get_sexo_display() or '',
            maestro.codigo or '',
            maestro.fecha_ingreso.strftime("%d/%m/%Y") if maestro.fecha_ingreso else '',
            maestro.form_academica or '',
            situacion,
            maestro.fecha_promocion.strftime("%d/%m/%Y") if maestro.fecha_promocion else '',
            maestro.get_est_civil_display() or '',
            maestro.telefono or '',
            maestro.get_status_display() or '',
            maestro.observaciones or '',
            escuela.get_sostenimiento_display() if escuela else '',
            desc_codigo
        ]
        ws.append(row)

    # Ajuste de ancho de columnas
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column].width = min(max_length + 2, 50)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="reporte_bd_horizontal.xlsx"'},
    )
    wb.save(response)

    return response

@login_required
@permission_required('gestion_escolar.acceder_reportes', raise_exception=True)
def reporteador_datos(request):
    """
    Muestra la página de selección de campos para el reporte personalizado.
    """
    # Definición de campos disponibles agrupados por categoría beneficiando al Maestro y Escuela
    campos_maestro = [
        ('id_maestro', 'ID Maestro'),
        ('a_paterno', 'Apellido Paterno'),
        ('a_materno', 'Apellido Materno'),
        ('nombres', 'Nombres'),
        ('curp', 'CURP'),
        ('rfc', 'RFC'),
        ('sexo', 'Sexo'),
        ('est_civil', 'Estado Civil'),
        ('fecha_nacimiento', 'Fecha de Nacimiento'),
        ('techo_f', 'Techo Financiero'),
        ('dep', 'Dependencia'),
        ('unid', 'Unidad'),
        ('sub_unid', 'Subunidad'),
        ('categog', 'Categoría'),
        ('hrs', 'Horas'),
        ('num_plaza', 'Número de Plaza'),
        ('codigo', 'Código'),
        ('fecha_ingreso', 'Fecha de Ingreso'),
        ('fecha_promocion', 'Fecha de Promoción'),
        ('form_academica', 'Formación Académica'),
        ('horario', 'Horario'),
        ('funcion', 'Función'),
        ('nivel_estudio', 'Nivel de Estudio'),
        ('domicilio_part', 'Domicilio Particular'),
        ('poblacion', 'Población'),
        ('codigo_postal', 'Código Postal'),
        ('telefono', 'Teléfono'),
        ('email', 'Email'),
        ('status', 'Status'),
        ('incentivo', 'Incentivo'),
        ('observaciones', 'Observaciones'),
        ('clave_presupuestal', 'Clave Presupuestal'),
    ]

    campos_escuela = [
        ('id_escuela', 'CCT (Clave)'),
        ('nombre_ct', 'Nombre del Centro de Trabajo'),
        ('zona_esc', 'Zona Escolar'),
        ('turno', 'Turno'),
        ('domicilio', 'Domicilio CCT'),
        ('telefono_ct', 'Teléfono CCT'),
        ('zona_economica', 'Zona Económica'),
        ('region', 'Región'),
        ('u_d', 'U.D.'),
        ('sostenimiento', 'Sostenimiento'),
    ]

    context = {
        'titulo': 'Reporteador de Datos Personalizado',
        'campos_maestro': campos_maestro,
        'campos_escuela': campos_escuela,
    }
    return render(request, 'gestion_escolar/reporteador_personalizado.html', context)

@permission_required('gestion_escolar.acceder_reportes', raise_exception=True)
def exportar_datos_dinamicos_excel(request):
    """
    Genera un archivo Excel dinámico basado en los campos seleccionados.
    """
    if request.method != 'POST':
        return redirect('reporteador_datos')

    campos_seleccionados = request.POST.getlist('campos')
    if not campos_seleccionados:
        messages.warning(request, "Debe seleccionar al menos un campo para exportar.")
        return redirect('reporteador_datos')

    # Diccionarios de mapeo para encabezados y acceso a datos
    mapeo_campos = {
        'id_maestro': 'ID Maestro',
        'a_paterno': 'APELLIDO PATERNO',
        'a_materno': 'APELLIDO MATERNO',
        'nombres': 'NOMBRES',
        'curp': 'CURP',
        'rfc': 'RFC',
        'sexo': 'SEXO',
        'est_civil': 'ESTADO CIVIL',
        'fecha_nacimiento': 'FECHA NACIMIENTO',
        'techo_f': 'TECHO FINANCIERO',
        'dep': 'DEPENDENCIA',
        'unid': 'UNIDAD',
        'sub_unid': 'SUBUNIDAD',
        'categog': 'CATEGORÍA',
        'hrs': 'HORAS',
        'num_plaza': 'NÚMERO DE PLAZA',
        'codigo': 'CÓDIGO',
        'fecha_ingreso': 'FECHA INGRESO',
        'fecha_promocion': 'FECHA PROMOCIÓN',
        'form_academica': 'FORMACIÓN ACADÉMICA',
        'horario': 'HORARIO',
        'funcion': 'FUNCIÓN',
        'nivel_estudio': 'NIVEL ESTUDIO',
        'domicilio_part': 'DOMICILIO PARTICULAR',
        'poblacion': 'POBLACIÓN',
        'codigo_postal': 'CÓDIGO POSTAL',
        'telefono': 'TELÉFONO',
        'email': 'EMAIL',
        'status': 'STATUS',
        'incentivo': 'INCENTIVO',
        'observaciones': 'OBSERVACIONES',
        'clave_presupuestal': 'CLAVE PRESUPUESTAL',
        
        # Campos de Escuela
        'id_escuela': 'CCT',
        'nombre_ct': 'NOMBRE CENTRO TRABAJO',
        'zona_esc': 'ZONA ESCOLAR',
        'turno': 'TURNO',
        'domicilio': 'DOMICILIO CCT',
        'telefono_ct': 'TELÉFONO CCT',
        'zona_economica': 'ZONA ECONÓMICA',
        'region': 'REGIÓN',
        'u_d': 'U.D.',
        'sostenimiento': 'SOSTENIMIENTO',
    }

    maestros_qs = Maestro.objects.select_related(
        'id_escuela', 
        'id_escuela__zona_esc', 
        'categog'
    ).prefetch_related('incentivos').all().order_by('a_paterno', 'a_materno', 'nombres')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte Personalizado"

    # Encabezados
    headers = [mapeo_campos.get(c, c.upper()) for c in campos_seleccionados]
    ws.append(headers)

    for maestro in maestros_qs:
        row = []
        escuela = maestro.id_escuela
        for campo in campos_seleccionados:
            valor = ''
            
            # Lógica para campos de Maestro
            if hasattr(maestro, campo):
                if campo == 'categog':
                    valor = maestro.categog.id_categoria if maestro.categog else ''
                elif campo == 'id_escuela':
                    valor = escuela.id_escuela if escuela else ''
                elif campo == 'incentivo':
                    valor = ", ".join([i.codigo for i in maestro.incentivos.all()])
                elif hasattr(maestro, f'get_{campo}_display'):
                    valor = getattr(maestro, f'get_{campo}_display')()
                else:
                    valor = getattr(maestro, campo)
                    if isinstance(valor, (datetime.date, datetime.datetime)):
                        valor = valor.strftime("%d/%m/%Y")
            
            # Lógica para campos de Escuela
            elif escuela and hasattr(escuela, campo):
                if campo == 'zona_esc':
                    valor = escuela.zona_esc.numero if escuela.zona_esc else ''
                elif hasattr(escuela, f'get_{campo}_display'):
                    valor = getattr(escuela, f'get_{campo}_display')()
                else:
                    valor = getattr(escuela, campo)
                    if isinstance(valor, (datetime.date, datetime.datetime)):
                        valor = valor.strftime("%d/%m/%Y")
            
            row.append(str(valor) if valor is not None else '')
        ws.append(row)

    # Ajuste de ancho de columnas
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column].width = min(max_length + 2, 50)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="reporte_personalizado.xlsx"'},
    )
    wb.save(response)

    return response


