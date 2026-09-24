from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from ..models import Zona, Escuela, Maestro, Categoria
from ..forms import ZonaForm, EscuelaForm, CategoriaForm
from .helpers import get_full_name

# Vistas para Zonas
def lista_zonas(request):
    if request.user.groups.filter(name='Directores').exists():
        raise PermissionDenied

    zonas = Zona.objects.select_related('supervisor').order_by('numero')

    # Resolver el supervisor por FUNCIÓN (SUPERVISOR) dentro de cada zona.
    # La FK zona.supervisor puede apuntar a un maestro sin dicha función (ATP, etc.),
    # por lo que se prioriza al maestro marcado como SUPERVISOR(A) en la zona.
    supervisores_por_zona = {
        z.id: m for z in zonas for m in (
            Maestro.objects.filter(
                id_escuela__zona_esc_id=z.id,
                funcion__in=['SUPERVISOR(A)'],
            )[:1]
        )
    }

    datos = []
    for zona in zonas:
        supervisor = supervisores_por_zona.get(zona.id) or zona.supervisor
        datos.append({
            'zona': zona,
            'supervisor': supervisor,
            'nombre_supervisor': get_full_name(supervisor) if supervisor else '',
        })

    return render(request, 'gestion_escolar/lista_zonas.html', {'zonas': datos})

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
    zona = get_object_or_404(Zona.objects.select_related('supervisor'), pk=pk)
    escuelas_en_zona = Escuela.objects.filter(zona_esc=zona).order_by('nombre_ct')
    
    context = {
        'zona': zona,
        'escuelas': escuelas_en_zona,
        'titulo': f"Detalle de la {zona.etiqueta}"
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
