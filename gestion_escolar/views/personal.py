from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse
from django.db.models import Q
from django.http import JsonResponse

from ..models import Maestro, Escuela, DocumentoExpediente
from ..forms import MaestroForm, DocumentoExpedienteForm
from .helpers import es_status_activo, FUNCION_MAPPING

# Vistas para Maestros
from unidecode import unidecode


def _normalizar_para_duplicado(txt):
    """Normaliza un texto para comparaciones de identidad (sin acentos, en mayúsculas)."""
    if not txt:
        return ''
    return unidecode(str(txt).strip().upper())


def persona_raiz(maestro):
    """Devuelve el registro raíz de la persona (recorre la cadena maestro_principal)."""
    m = maestro
    vistos = set()
    while m and m.maestro_principal:
        if m.id_maestro in vistos:
            break
        vistos.add(m.id_maestro)
        m = m.maestro_principal
    return m


def registros_de_persona(maestro):
    """IDs de todos los registros que pertenecen a la misma persona (raíz + plazas secundarias)."""
    raiz = persona_raiz(maestro)
    if raiz is None:
        return [maestro.id_maestro]
    ids = [raiz.id_maestro]
    ids += list(Maestro.objects.filter(maestro_principal=raiz).values_list('id_maestro', flat=True))
    return ids


def buscar_persona_existente(datos):
    """
    Busca si ya existe un registro de la misma persona antes de crearla.
    Prioriza CURP; si no hay CURP, busca por nombre completo normalizado.
    Excluye el propio registro en ediciones.
    """
    curp = datos.get('curp')
    exclude_pk = datos.get('exclude_pk')
    qs_base = Maestro.objects.all()
    if exclude_pk:
        qs_base = qs_base.exclude(id_maestro=exclude_pk)

    if curp:
        curp_limpio = curp.strip().upper()
        qs = qs_base.filter(curp__iexact=curp_limpio)
        if qs.exists():
            return qs.first()

    nombres = datos.get('nombres')
    a_paterno = datos.get('a_paterno')
    a_materno = datos.get('a_materno')
    if all(v is not None for v in [nombres, a_paterno, a_materno]) and any([nombres, a_paterno, a_materno]):
        paterno_n = _normalizar_para_duplicado(a_paterno)
        materno_n = _normalizar_para_duplicado(a_materno)
        nombres_n = _normalizar_para_duplicado(nombres)
        qs_nombre = qs_base.filter(
            a_paterno_normalized=paterno_n or None,
            a_materno_normalized=materno_n or None,
            nombres_normalized=nombres_n or None,
        )
        if qs_nombre.exists():
            return qs_nombre.first()
    return None


def _verificar_directores_duplicados(request, maestro_guardado):
    """Tras guardar un maestro, si este quedó con función DIRECTOR(A) y su C.T.
    ya tiene otro maestro ACTIVO también marcado como director, emite un aviso
    para que el usuario resuelva manualmente quién es el director real."""
    if (maestro_guardado.funcion or '') != 'DIRECTOR(A)':
        return
    escuela = maestro_guardado.id_escuela
    if not escuela:
        return
    otros = Maestro.objects.filter(
        id_escuela=escuela,
        funcion='DIRECTOR(A)',
    ).exclude(id_maestro=maestro_guardado.id_maestro)
    activos = [m for m in otros if es_status_activo(m.status)]
    extra = activos or list(otros)
    if not extra:
        return
    nombres = ', '.join(f"{m.nombres} {m.a_paterno} (ID {m.id_maestro})" for m in extra)
    messages.warning(
        request,
        f"Advertencia: el C.T. {escuela.id_escuela} ya tiene a otro maestro con "
        f"función DIRECTOR(A): {nombres}. Revisa manualmente cuál es el director real "
        "para evitar duplicados."
    )

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

    # Agrupar por persona: si 'agrupar' está activo, solo se muestran los
    # registros raíz (maestro_principal NULL). Las plazas adicionales siguen
    # visibles como badge "+N" y en la vista de detalle.
    agrupar = request.GET.get('agrupar', '1') != '0'
    if agrupar:
        from django.db.models import Count
        queryset = queryset.filter(maestro_principal__isnull=True).annotate(
            n_plazas_sec=Count('plazas_secundarias', distinct=True)
        )

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
        status_map = {'ACTIVO': 'success', 'INACTIVO': 'danger'}
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
            is_interino,
            getattr(maestro, 'n_plazas_sec', 0) if agrupar else 0
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
            maestro.clave_presupuestal = maestro.generar_clave_presupuestal()

            existente = buscar_persona_existente({
                'curp': maestro.curp,
                'nombres': maestro.nombres,
                'a_paterno': maestro.a_paterno,
                'a_materno': maestro.a_materno,
            })

            if existente:
                ids_persona = registros_de_persona(existente)
                claves_existentes = set(
                    Maestro.objects.filter(id_maestro__in=ids_persona)
                    .exclude(clave_presupuestal__isnull=True)
                    .exclude(clave_presupuestal='')
                    .values_list('clave_presupuestal', flat=True)
                )
                if maestro.clave_presupuestal and maestro.clave_presupuestal in claves_existentes:
                    form.add_error(
                        None,
                        f'Ya existe un registro de esta persona con la clave presupuestal '
                        f'{maestro.clave_presupuestal} (ID {existente.id_maestro}). No se guardó '
                        'para evitar un duplicado. Revisa el registro existente.'
                    )
                    return render(request, 'gestion_escolar/form_maestro.html', {
                        'form': form,
                        'titulo': 'Agregar Maestro',
                        'all_escuelas': all_escuelas
                    })
                else:
                    raiz = persona_raiz(existente)
                    maestro.maestro_principal = raiz
                    maestro.save()
                    messages.success(
                        request,
                        f'Maestro agregado correctamente como plaza secundaria de la persona '
                        f'(CURP {existente.curp or "s/nombre"}, ID raíz {raiz.id_maestro if raiz else existente.id_maestro}). '
                        'No se creó un registro duplicado.'
                    )
            else:
                maestro.save()
                messages.success(request, 'Maestro agregado correctamente.')

            _verificar_directores_duplicados(request, maestro)
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
                _verificar_directores_duplicados(request, maestro)
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

    # --- Historial de interinatos de la persona (todas sus plazas) ---
    from ..models import Interinato
    ids_persona = registros_de_persona(maestro)
    interinatos_cubiertos = Interinato.objects.filter(
        maestro_interino_id__in=ids_persona
    ).select_related('maestro_titular', 'escuela').order_by('-fecha_inicio')
    interinatos_como_titular = Interinato.objects.filter(
        maestro_titular_id__in=ids_persona
    ).select_related('maestro_interino', 'escuela').order_by('-fecha_inicio')

    context = {
        'maestro': maestro,
        'documentos': documentos,
        'form': form,
        'titulo': 'Detalle del Personal',
        'maestro_anterior': maestro_anterior,
        'maestro_siguiente': maestro_siguiente,
        'otras_plazas': otras_plazas,
        'maestro_raiz': maestro_raiz,
        'interinatos_cubiertos': interinatos_cubiertos,
        'interinatos_como_titular': interinatos_como_titular,
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
    funcion_info = FUNCION_MAPPING.get(funcion)
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


@login_required
def reporte_personas_vs_plazas(request):
    from .helpers import contar_personal
    from django.db.models import Count

    total = contar_personal()

    # Lista de personas (raíces / agrupadas por CURP)
    personas = []
    multiplas = 0
    raices = (Maestro.objects.filter(maestro_principal__isnull=True)
              .order_by('a_paterno', 'a_materno', 'nombres'))
    for raiz in raices:
        placas = [raiz] + list(raiz.plazas_secundarias.order_by('id_maestro'))
        n_plazas = len(placas)
        if n_plazas > 1:
            multiplas += 1
        personas.append({
            'raiz': raiz,
            'plazas': placas,
            'n_plazas': n_plazas,
            'n_activas': sum(1 for p in placas if es_status_activo(p.status)),
        })

    # Maestros sin CURP (personas individuales)
    sin_curp = Maestro.objects.filter(curp__isnull=True).count() + Maestro.objects.filter(curp='').count()

    return render(request, 'gestion_escolar/reporte_personas_plazas.html', {
        'total': total,
        'multiplas': multiplas,
        'personas': personas,
        'sin_curp': sin_curp,
        'titulo': 'Reporte de Personas vs Plazas',
    })
