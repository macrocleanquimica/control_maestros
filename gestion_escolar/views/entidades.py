from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models.deletion import ProtectedError

from ..models import Zona, Escuela, Maestro, Categoria
from ..forms import ZonaForm, EscuelaForm, CategoriaForm
from .helpers import get_full_name

# Vistas para Zonas
@login_required
@permission_required('gestion_escolar.view_zona', raise_exception=True)
def lista_zonas(request):
    if request.user.groups.filter(name='Directores').exists():
        raise PermissionDenied

    zonas = Zona.objects.select_related('supervisor').order_by('numero')

    # Resolver el supervisor con la definición única (función SUPERVISOR activa
    # con nombre; respaldo en la FK manual zona.supervisor). Ver helpers.
    from .helpers import elegir_supervisor_activo, _supervisor_fk_valido
    supervisores_por_zona = {}
    for z in zonas:
        sup = elegir_supervisor_activo(z)
        if sup is None and _supervisor_fk_valido(z.supervisor):
            sup = z.supervisor
        if sup is not None:
            supervisores_por_zona[z.id] = sup

    datos = []
    for zona in zonas:
        supervisor = supervisores_por_zona.get(zona.id) or zona.supervisor
        datos.append({
            'zona': zona,
            'supervisor': supervisor,
            'nombre_supervisor': get_full_name(supervisor) if supervisor else '',
        })

    return render(request, 'gestion_escolar/lista_zonas.html', {'zonas': datos})

@login_required
@permission_required('gestion_escolar.add_zona', raise_exception=True)
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

@login_required
@permission_required('gestion_escolar.change_zona', raise_exception=True)
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

@login_required
@permission_required('gestion_escolar.delete_zona', raise_exception=True)
def eliminar_zona(request, pk):
    zona = get_object_or_404(Zona, pk=pk)
    n_escuelas = Escuela.objects.filter(zona_esc=zona).count()
    n_personal = Maestro.objects.filter(id_escuela__zona_esc=zona).count()
    bloqueado = bool(n_escuelas)
    if request.method == 'POST':
        if bloqueado:
            messages.error(
                request,
                f'No se puede eliminar: la zona tiene {n_escuelas} escuela(s) y '
                f'{n_personal} registro(s) de personal. Reasigne primero sus '
                'escuelas a otra zona desde Editar Escuela.'
            )
            return redirect('lista_zonas')
        try:
            zona.delete()
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar: la zona todavía tiene escuelas asignadas. '
                'Reasigne primero sus escuelas a otra zona.'
            )
            return redirect('lista_zonas')
        messages.success(request, 'Zona eliminada correctamente.')
        return redirect('lista_zonas')
    return render(request, 'gestion_escolar/eliminar_zona.html', {
        'zona': zona, 'n_escuelas': n_escuelas,
        'n_personal': n_personal, 'bloqueado': bloqueado,
    })

@login_required
@permission_required('gestion_escolar.view_zona', raise_exception=True)
def detalle_zona(request, pk):
    zona = get_object_or_404(Zona.objects.select_related('supervisor'), pk=pk)
    escuelas_en_zona = Escuela.objects.filter(zona_esc=zona).order_by('nombre_ct')
    
    context = {
        'zona': zona,
        'escuelas': escuelas_en_zona,
        'titulo': f"Detalle de la {zona.etiqueta}"
    }
    
    return render(request, 'gestion_escolar/detalle_zona.html', context)


# Vistas para Escuelas
@login_required
@permission_required('gestion_escolar.view_escuela', raise_exception=True)
def lista_escuelas(request):
    if request.user.groups.filter(name='Directores').exists():
        raise PermissionDenied
    escuelas = Escuela.objects.all().order_by('nombre_ct')
    return render(request, 'gestion_escolar/lista_escuelas.html', {'escuelas': escuelas})

@login_required
@permission_required('gestion_escolar.add_escuela', raise_exception=True)
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

@login_required
@permission_required('gestion_escolar.change_escuela', raise_exception=True)
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

@login_required
@permission_required('gestion_escolar.delete_escuela', raise_exception=True)
def eliminar_escuela(request, pk):
    escuela = get_object_or_404(Escuela, pk=pk)
    n_personal = Maestro.objects.filter(id_escuela=escuela).count()
    n_regulares = escuela.escuelas_regulares.count()
    bloqueado = bool(n_personal or n_regulares)
    if request.method == 'POST':
        if bloqueado:
            messages.error(
                request,
                f'No se puede eliminar: la escuela tiene {n_personal} registro(s) '
                f'de personal y {n_regulares} escuela(s) regular(es) atendida(s). '
                'Reubique primero su personal (cambio de adscripción o INACTIVO).'
            )
            return redirect('lista_escuelas')
        try:
            escuela.delete()
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar: la escuela todavía tiene personal o '
                'escuelas regulares asignadas.'
            )
            return redirect('lista_escuelas')
        messages.success(request, 'Escuela eliminada correctamente.')
        return redirect('lista_escuelas')
    return render(request, 'gestion_escolar/eliminar_escuela.html', {
        'escuela': escuela, 'n_personal': n_personal,
        'n_regulares': n_regulares, 'bloqueado': bloqueado,
    })

@login_required
@permission_required('gestion_escolar.view_escuela', raise_exception=True)
def detalle_escuela(request, pk):
    escuela = get_object_or_404(Escuela, pk=pk)
    from django.db.models import Case, When, Value, IntegerField
    # Activos primero, luego licencias, luego inactivos.
    personal = Maestro.objects.filter(id_escuela=escuela).annotate(
        _orden_status=Case(
            When(status='ACTIVO', then=Value(0)),
            When(status='LICENCIA', then=Value(1)),
            When(status='INACTIVO', then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    ).order_by('_orden_status', 'a_paterno', 'a_materno', 'nombres')
    
    # Buscar director por el maestro activo adecuado (E0629 primero, luego responsable)
    from .helpers import elegir_director_activo
    director = elegir_director_activo(escuela)

    # Verificar si es un CCT FUA (atiende escuelas regulares)
    es_fua = 'FUA' in escuela.id_escuela.upper()
    escuelas_regulares = escuela.escuelas_regulares.all() if es_fua else []
        
    context = {
        'escuela': escuela,
        'personal': personal,
        'director_escuela': director,
        'titulo': 'Detalle de la Escuela',
        'es_fua': es_fua,
        'escuelas_regulares': escuelas_regulares,
    }
    return render(request, 'gestion_escolar/detalle_escuela.html', context)

# Vistas para Categorías
@login_required
@permission_required('gestion_escolar.view_categoria', raise_exception=True)
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

@login_required
@permission_required('gestion_escolar.change_categoria', raise_exception=True)
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

@login_required
@permission_required('gestion_escolar.delete_categoria', raise_exception=True)
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoría eliminada correctamente.')
        return redirect('lista_categorias')
    return render(request, 'gestion_escolar/eliminar_categoria.html', {'categoria': categoria})
