from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from ..models import Prelacion, MotivoTramite, PlantillaTramite, Maestro
from .helpers import es_director, escuela_de_director


def _puede_buscar_maestros(user):
    """Buscador de maestros (solo id + nombre) para formularios que lo requieren.

    Además de quien consulta Personal, lo necesitan quienes registran
    correspondencia o trámites. No expone datos personales y no da acceso
    al módulo de Personal.
    """
    return (
        user.is_superuser
        or user.has_perm('gestion_escolar.view_maestro')
        or user.has_perm('gestion_escolar.add_registrocorrespondencia')
        or user.has_perm('gestion_escolar.change_registrocorrespondencia')
    )


def _rechazar_si_fuera_de_escuela(request, maestro):
    """403 si el director consulta personal de otra escuela. Para no directores no hace nada."""
    if not es_director(request.user):
        return
    escuela_dir = escuela_de_director(request.user)
    cct_dir = (escuela_dir.id_escuela or '').strip().upper() if escuela_dir and escuela_dir.id_escuela else ''
    cct_mtro = (maestro.id_escuela.id_escuela or '').strip().upper() if maestro.id_escuela and maestro.id_escuela.id_escuela else ''
    if not cct_dir or cct_mtro != cct_dir:
        raise PermissionDenied


def _filtrar_escuela_director(request, queryset):
    """Limita el queryset a la escuela del director. Para no directores lo devuelve igual."""
    if not es_director(request.user):
        return queryset
    escuela_dir = escuela_de_director(request.user)
    if escuela_dir is None:
        return queryset.none()
    return queryset.filter(id_escuela=escuela_dir)

# Vista AJAX para obtener datos de prelación
@login_required
def get_prelacion_data_ajax(request):
    curp = request.GET.get('curp')
    rfc = request.GET.get('rfc')
    nombre = request.GET.get('nombre')
    
    datos_prelacion = {
        'encontrado': False,
        'numero_prelacion': '',
        'folio_prelacion': '',
        'tipo_val': '',
        'nombre_prelacion': ''
    }

    if curp or rfc or nombre:
        try:
            # Primero intentar por CURP o RFC
            query = Q()
            if curp:
                query |= Q(curp=curp.strip())
            if rfc:
                query |= Q(curp=rfc.strip())
                
            prelacion = None
            if query:
                prelacion = Prelacion.objects.filter(query).first()
            
            # Si no se encuentra, intentar por nombre completo (si se proporcionó)
            if not prelacion and nombre:
                from unidecode import unidecode
                nombre_norm = unidecode(nombre.upper().strip())
                # Buscamos coincidencias aproximadas en el nombre
                prelacion = Prelacion.objects.filter(nombre__icontains=nombre_norm).first()
            
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

@login_required
def get_motivos_tramite_ajax(request):
    plantilla_id = request.GET.get('plantilla_id')
    motivos_filtrados = []

    if plantilla_id:
        try:
            plantilla = PlantillaTramite.objects.get(id=plantilla_id)
            from gestion_escolar.motivos_plantilla import ids_permitidos
            ids = ids_permitidos(plantilla.nombre)

            if ids is None:
                # Plantilla desconocida (legado): todos los motivos.
                motivos_filtrados_qs = MotivoTramite.objects.all().order_by('motivo_tramite')
            elif ids:
                motivos_filtrados_qs = MotivoTramite.objects.filter(id__in=ids).order_by('motivo_tramite')
            else:
                # Plantilla explícitamente sin motivo: lista vacía.
                motivos_filtrados_qs = MotivoTramite.objects.none()

            for motivo in motivos_filtrados_qs:
                motivos_filtrados.append({'id': motivo.id, 'text': motivo.motivo_tramite})

        except PlantillaTramite.DoesNotExist:
            pass

    return JsonResponse(motivos_filtrados, safe=False)

@login_required
@permission_required('gestion_escolar.view_maestro', raise_exception=True)
def verificar_curp_ajax(request):
    """Revisa si una CURP ya existe en personal (comparación exacta,
    insensible a mayúsculas/espacios). Se usa al dar de alta para impedir
    duplicar al trabajador: si existe, hay que agregarle la plaza."""
    from django.urls import reverse
    curp = (request.GET.get('curp') or '').strip()
    exclude_id = (request.GET.get('exclude_id') or '').strip()
    if not curp:
        return JsonResponse({'existe': False, 'coincidencias': []})
    qs = Maestro.objects.filter(curp__iexact=curp)
    qs = _filtrar_escuela_director(request, qs)
    if exclude_id:
        qs = qs.exclude(id_maestro=exclude_id)
    coincidencias = []
    for m in qs.order_by('id_maestro')[:5]:
        cct = m.id_escuela.id_escuela if m.id_escuela else ''
        coincidencias.append({
            'id': m.id_maestro,
            'nombre': f"{m.nombres or ''} {m.a_paterno or ''} {m.a_materno or ''}".strip(),
            'cct': cct,
            'status': m.status or '',
            'clave': m.clave_presupuestal or '',
            'detalle_url': reverse('detalle_maestro', args=[m.id_maestro]),
            'agregar_plaza_url': reverse('agregar_otra_plaza', args=[m.id_maestro]),
        })
    return JsonResponse({'existe': bool(coincidencias), 'coincidencias': coincidencias})


@login_required
def buscar_maestros_ajax(request):
    if not _puede_buscar_maestros(request.user):
        raise PermissionDenied
    search_term = request.GET.get('term', '')
    
    if not search_term or len(search_term) < 2:
        return JsonResponse({'results': []})
    
    from unidecode import unidecode
    # Normalizamos el término de búsqueda (mayúsculas y sin acentos)
    search_unaccented = unidecode(search_term.upper())

    # Buscamos en el campo pre-calculado y normalizado (nombre)
    query_nombre = Q(nombre_completo_unaccented__icontains=search_unaccented)
    
    # También buscamos por clave presupuestal
    query_clave = Q(clave_presupuestal__icontains=search_term.upper())
    
    # Combinamos ambas búsquedas con OR
    query = query_nombre | query_clave
    
    maestros = Maestro.objects.filter(query).order_by('nombres', 'a_paterno', 'a_materno')
    maestros = _filtrar_escuela_director(request, maestros)[:20]
    
    results = []
    for maestro in maestros:
        # Formato de nombre: Nombres Apellido Paterno Apellido Materno
        full_name = f"{maestro.nombres or ''} {maestro.a_paterno or ''} {maestro.a_materno or ''}".strip()
        
        # Agregar la clave presupuestal al texto mostrado
        if maestro.clave_presupuestal:
            display_text = f"{full_name} - Clave: {maestro.clave_presupuestal}"
        else:
            display_text = full_name
            
        results.append({
            "id": maestro.id_maestro,
            "text": display_text
        })
    
    return JsonResponse({'results': results})

@login_required
@permission_required('gestion_escolar.view_maestro', raise_exception=True)
def get_maestro_data_ajax(request):
    maestro_id = request.GET.get('maestro_id')

    data = {}
    if maestro_id:
        try:
            maestro = Maestro.objects.prefetch_related('incentivos').get(id_maestro=maestro_id)
            _rechazar_si_fuera_de_escuela(request, maestro)
            incentivos_str = ", ".join([i.codigo for i in maestro.incentivos.all()])
            data = {
                'nombre_completo': f"{maestro.nombres or ''} {maestro.a_paterno or ''} {maestro.a_materno or ''}".strip(),
                'curp': maestro.curp or '',
                'rfc': maestro.rfc or '',
                'clave_presupuestal': maestro.clave_presupuestal or '',
                'categoria': maestro.categog.descripcion if maestro.categog else '',
                'funcion': maestro.funcion or '',
                'form_academica': maestro.form_academica or '',
                'ze_techo_f': '', # Placeholder
                'incentivos': incentivos_str,
                'escuela_cct': maestro.id_escuela.id_escuela if maestro.id_escuela else '',
                'escuela_nombre': maestro.id_escuela.nombre_ct if maestro.id_escuela else '',
            }
            # Obtener ZE del techo financiero
            if maestro.techo_f:
                from ..models import Escuela
                escuela_pago = Escuela.objects.filter(id_escuela=maestro.techo_f).first()
                if escuela_pago:
                    data['ze_techo_f'] = escuela_pago.zona_economica or ''
        except Maestro.DoesNotExist:
            data = {'error': 'Maestro no encontrado'}
    return JsonResponse(data)

@login_required
@permission_required('gestion_escolar.view_maestro', raise_exception=True)
def get_maestro_data_for_vacancia(request):
    maestro_id = request.GET.get('maestro_id')
    data = {}
    if maestro_id:
        try:
            maestro = Maestro.objects.get(id_maestro=maestro_id)
            _rechazar_si_fuera_de_escuela(request, maestro)
            data = {
                'nombre_completo': f'{maestro.nombres} {maestro.a_paterno} {maestro.a_materno}',
                'clave_presupuestal': maestro.clave_presupuestal,
                'categoria': maestro.categog.id_categoria if maestro.categog else '',
                'curp': maestro.curp or ''
            }
        except Maestro.DoesNotExist:
            data = {'error': 'Maestro no encontrado'}
    return JsonResponse(data)

@login_required
@permission_required('gestion_escolar.view_maestro', raise_exception=True)
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
            _rechazar_si_fuera_de_escuela(request, maestro)
            data['curp_interino'] = maestro.curp or ''

            if maestro.curp:
                prelacion = Prelacion.objects.filter(curp=maestro.curp).first()
                if prelacion:
                    data['folio_prelacion'] = prelacion.folio or ''
                    data['posicion_orden'] = prelacion.pos_orden or ''
                    data['tipo_val'] = prelacion.tipo_val or ''

        except Maestro.DoesNotExist:
            data['error'] = 'Maestro interino no encontrado.'
            data['curp_interino'] = 'N/A'
        except Exception as e:
            data['error'] = f'Error inesperado: {str(e)}'
            data['curp_interino'] = 'Error'

    return JsonResponse(data)

@login_required
@permission_required('gestion_escolar.view_escuela', raise_exception=True)
def buscar_escuelas_ajax(request):
    search_term = request.GET.get('term', '')
    
    if not search_term or len(search_term) < 2:
        return JsonResponse({'results': []})
    
    from ..models import Escuela
    from unidecode import unidecode
    
    # Normalizamos el término de búsqueda
    search_norm = unidecode(search_term.upper())

    # Búsqueda por CCT o por Nombre
    query = Q(id_escuela__icontains=search_term.upper()) | Q(nombre_ct__icontains=search_norm)
    
    escuelas = Escuela.objects.filter(query).order_by('id_escuela')[:20]
    
    results = []
    for escuela in escuelas:
        results.append({
            "id": escuela.id_escuela,
            "text": f"{escuela.nombre_ct} ({escuela.id_escuela})"
        })
    
    return JsonResponse({'results': results})
