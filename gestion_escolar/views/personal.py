from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse
from django.db.models import Q
from django.http import JsonResponse

from ..models import Maestro, Escuela, DocumentoExpediente
from ..forms import MaestroForm, DocumentoExpedienteForm

# Vistas para Maestros
from unidecode import unidecode

@login_required
def lista_maestros(request):
    user = request.user
    return render(request, 'gestion_escolar/lista_maestros.html')

@login_required
def lista_maestros_ajax(request):
    draw = int(request.GET.get('draw', 0))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    order_column_index = int(request.GET.get('order[0][column]', 0))
    order_dir = request.GET.get('order[0][dir]', 'asc')
    column_names = ['id_maestro', 'a_paterno', 'id_escuela__id_escuela', 'curp', 'clave_presupuestal', 'status']
    order_column = column_names[order_column_index]
    if order_dir == 'desc':
        order_column = f'-{order_column}'

    user = request.user
    if user.groups.filter(name='Directores').exists():
        try:
            maestro_director = user.maestro_profile
            queryset = Maestro.objects.filter(id_escuela=maestro_director.id_escuela)
        except AttributeError:
            queryset = Maestro.objects.none()
    else:
        queryset = Maestro.objects.all()
    
    queryset = queryset.select_related('id_escuela')
    queryset = queryset.exclude(id_maestro__isnull=True).exclude(id_maestro='')

    records_total = queryset.count()

    if search_value:
        from unidecode import unidecode
        # Normalizamos el término de búsqueda para el nombre (mayúsculas y sin acentos)
        search_unaccented = unidecode(search_value.upper())

        # Búsqueda en campos que no necesitan normalización especial (o usan la entrada directa)
        query = Q(id_maestro__icontains=search_value) | \
                Q(curp__icontains=search_value) | \
                Q(rfc__icontains=search_value) | \
                Q(clave_presupuestal__icontains=search_value) | \
                Q(id_escuela__id_escuela__icontains=search_value) | \
                Q(nombre_completo_unaccented__icontains=search_unaccented)

        queryset = queryset.filter(query)

    records_filtered = queryset.count()
    queryset = queryset.order_by(order_column)[start:start + length]

    data = []
    for maestro in queryset:
        actions = '<div class="d-flex gap-1 justify-content-center">'
        actions += f'<a href="{reverse("detalle_maestro", args=[maestro.pk])}" class="btn btn-sm btn-light border btn-action-custom" title="Ver Detalle"><i class="fas fa-eye text-info"></i></a>'
        
        if request.user.has_perm('gestion_escolar.change_maestro'):
            actions += f'<a href="{reverse("editar_maestro", args=[maestro.pk])}" class="btn btn-sm btn-light border btn-action-custom" title="Editar"><i class="fas fa-edit text-primary"></i></a>'

        if request.user.has_perm('gestion_escolar.delete_maestro'):
            actions += f'<a href="{reverse("eliminar_maestro", args=[maestro.pk])}" class="btn btn-sm btn-light border btn-action-custom" title="Eliminar"><i class="fas fa-trash text-danger"></i></a>'
        
        actions += '</div>'
        status_map = {'ACTIVO': 'success', 'INACTIVO': 'warning'}
        status_class = status_map.get(maestro.status, 'secondary')
        status_html = f'<span class="badge bg-{status_class}">{maestro.get_status_display()}</span>'

        is_misplaced = False
        if maestro.id_escuela and maestro.techo_f:
            if maestro.id_escuela.id_escuela.strip().upper() != maestro.techo_f.strip().upper():
                is_misplaced = True

        is_interino = False
        if maestro.codigo and maestro.codigo.strip() not in ['10', '96', '95', '09']:
            is_interino = True

        data.append([
            maestro.id_maestro,
            f'{maestro.nombres} {maestro.a_paterno} {maestro.a_materno}',
            maestro.id_escuela.id_escuela if maestro.id_escuela else 'N/A',
            maestro.curp,
            maestro.clave_presupuestal or '-',
            status_html,
            actions,
            is_misplaced,
            is_interino
        ])

    response = {
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
    }
    return JsonResponse(response)

def agregar_maestro(request):
    all_escuelas = Escuela.objects.all()
    initial_data = {}
    escuela_id = request.GET.get('escuela_id')
    if escuela_id:
        try:
            escuela = Escuela.objects.get(pk=escuela_id)
            initial_data['id_escuela'] = escuela
        except Escuela.DoesNotExist:
            pass

    if request.method == 'POST':
        form = MaestroForm(request.POST, request=request)
        if form.is_valid():
            maestro = form.save(commit=False)
            maestro.save()
            messages.success(request, 'Maestro agregado correctamente.')
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
            form = MaestroForm(instance=maestro, request=request)
        else:
            form = MaestroForm(request.POST, instance=maestro, request=request)
            if form.is_valid():
                form.save()
                messages.success(request, 'Maestro actualizado correctamente.')
                return redirect('lista_maestros')
            else:
                print(form.errors.as_json())
                messages.error(request, 'Por favor corrige los errores.')
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
        messages.success(request, 'Maestro eliminada correctamente.')
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

    # Navegación anterior / siguiente (ordenado por id_maestro)
    qs_base = Maestro.objects.exclude(id_maestro__isnull=True).exclude(id_maestro='').order_by('id_maestro')
    maestro_anterior = qs_base.filter(id_maestro__lt=pk).last()
    maestro_siguiente = qs_base.filter(id_maestro__gt=pk).first()

    # --- Detección de otras plazas del mismo personal ---
    # Opción 1: Por CURP (detección automática)
    otras_por_curp = Maestro.objects.none()
    if maestro.curp:
        otras_por_curp = Maestro.objects.filter(
            curp=maestro.curp
        ).exclude(id_maestro=maestro.id_maestro)

    # Opción 3: Por vínculo directo (maestro_principal)
    # Determinar el maestro raíz (el principal de la cadena)
    if maestro.maestro_principal:
        maestro_raiz = maestro.maestro_principal
    else:
        maestro_raiz = None

    otras_por_vinculo = Maestro.objects.none()
    if maestro_raiz:
        # Traer el registro principal + sus demás secundarios (hermanos)
        otras_por_vinculo = Maestro.objects.filter(
            Q(id_maestro=maestro_raiz.id_maestro) |
            Q(maestro_principal=maestro_raiz)
        ).exclude(id_maestro=maestro.id_maestro)
    else:
        # Este registro es el principal; traer sus plazas secundarias directas
        otras_por_vinculo = maestro.plazas_secundarias.all()

    # Combinar ambas listas y eliminar duplicados
    otras_plazas = (otras_por_curp | otras_por_vinculo).distinct()

    context = {
        'maestro': maestro,
        'documentos': documentos,
        'form': form,
        'titulo': 'Detalle del Personal',
        'maestro_anterior': maestro_anterior,
        'maestro_siguiente': maestro_siguiente,
        'otras_plazas': otras_plazas,
        'maestro_raiz': maestro_raiz,
    }
    return render(request, 'gestion_escolar/detalle_maestro.html', context)
    

@login_required
@permission_required('gestion_escolar.change_maestro', raise_exception=True)
def agregar_otra_plaza(request, pk):
    """
    Crea un nuevo registro de maestro clonando los datos personales del original.
    Establece automáticamente el maestro_principal.
    """
    maestro_original = get_object_or_404(Maestro, id_maestro=pk)
    
    # Determinar quién será el maestro_principal del nuevo registro
    # Si el original ya tiene un principal, ese sigue siendo el principal para todos
    maestro_raiz = maestro_original.maestro_principal if maestro_original.maestro_principal else maestro_original

    if request.method == 'POST':
        form = MaestroForm(request.POST, request=request)
        if form.is_valid():
            nueva_plaza = form.save(commit=False)
            nueva_plaza.maestro_principal = maestro_raiz
            nueva_plaza.save()
            messages.success(request, f'Nueva plaza agregada correctamente para {maestro_original.nombres}.')
            return redirect('detalle_maestro', pk=nueva_plaza.id_maestro)
    else:
        # Datos personales a clonar
        initial_data = {
            'nombres': maestro_original.nombres,
            'a_paterno': maestro_original.a_paterno,
            'a_materno': maestro_original.a_materno,
            'curp': maestro_original.curp,
            'rfc': maestro_original.rfc,
            'fecha_nacimiento': maestro_original.fecha_nacimiento,
            'sexo': maestro_original.sexo,
            'est_civil': maestro_original.est_civil,
            'domicilio_part': maestro_original.domicilio_part,
            'poblacion': maestro_original.poblacion,
            'codigo_postal': maestro_original.codigo_postal,
            'telefono': maestro_original.telefono,
            'email': maestro_original.email,
            'nivel_estudio': maestro_original.nivel_estudio,
            'form_academica': maestro_original.form_academica,
            'maestro_principal': maestro_raiz,
        }
        form = MaestroForm(initial=initial_data, request=request)

    return render(request, 'gestion_escolar/form_maestro.html', {
        'form': form,
        'titulo': f'Agregar Nueva Plaza para {maestro_original.nombres}',
        'maestro': maestro_original,
        'es_clonado': True
    })


@login_required
def eliminar_documento_expediente(request, doc_pk):
    documento = get_object_or_404(DocumentoExpediente, pk=doc_pk)
    maestro_id = documento.maestro.id_maestro

    if request.method == 'POST':
        try:
            documento.archivo.delete(save=False)
            documento.delete()
            messages.success(request, 'Documento eliminado correctamente.')
            return redirect('detalle_maestro', pk=maestro_id)
        except Exception as e:
            messages.error(request, f"Error al eliminar el documento: {e}")
            return redirect('detalle_maestro', pk=maestro_id)

    context = {
        'documento': documento,
        'maestro': documento.maestro,
    }
    return render(request, 'gestion_escolar/eliminar_documento_expediente.html', context)

# Vistas para diferentes funciones
def lista_por_funcion(request, funcion):
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

    funcion_info = funcion_mapping.get(funcion)
    if not funcion_info:
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
