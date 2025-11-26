from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from ..models import FUP, Maestro, KardexMovimiento
from ..forms import FUPForm
from django.core.paginator import Paginator
from django.db.models import Q

@login_required
@permission_required('gestion_escolar.acceder_fup', raise_exception=True)
def lista_fup(request):
    fups = FUP.objects.all().order_by('-fecha', '-id')
    return render(request, 'gestion_escolar/lista_fup.html', {'fups': fups})

@login_required
@permission_required('gestion_escolar.add_fup', raise_exception=True)
def crear_fup(request):
    if request.method == 'POST':
        form = FUPForm(request.POST, request.FILES)
        if form.is_valid():
            fup = form.save(commit=False)
            fup.usuario = request.user
            fup.save()
            
            # Crear registro en Kardex
            KardexMovimiento.objects.create(
                maestro=fup.maestro,
                usuario=request.user,
                descripcion=f"SE CAPTURÓ FUP CON FOLIO {fup.folio}"
            )
            
            messages.success(request, 'FUP creado exitosamente y registrado en el kardex.')
            return redirect('lista_fup')
    else:
        form = FUPForm()
    
    return render(request, 'gestion_escolar/form_fup.html', {'form': form, 'titulo': 'Capturar FUP'})

@login_required
@permission_required('gestion_escolar.change_fup', raise_exception=True)
def editar_fup(request, pk):
    fup = get_object_or_404(FUP, pk=pk)
    if request.method == 'POST':
        form = FUPForm(request.POST, request.FILES, instance=fup)
        if form.is_valid():
            form.save()
            messages.success(request, 'FUP actualizado exitosamente.')
            return redirect('lista_fup')
    else:
        form = FUPForm(instance=fup)
    
    return render(request, 'gestion_escolar/form_fup.html', {'form': form, 'titulo': 'Editar FUP'})

@login_required
@permission_required('gestion_escolar.delete_fup', raise_exception=True)
def eliminar_fup(request, pk):
    fup = get_object_or_404(FUP, pk=pk)
    if request.method == 'POST':
        fup.delete()
        messages.success(request, 'FUP eliminado exitosamente.')
        return redirect('lista_fup')
    return render(request, 'gestion_escolar/eliminar_fup.html', {'fup': fup})

@login_required
@permission_required('gestion_escolar.view_fup', raise_exception=True)
def detalle_fup(request, pk):
    fup = get_object_or_404(FUP, pk=pk)
    return render(request, 'gestion_escolar/detalle_fup.html', {'fup': fup})

@login_required
def get_maestro_data_fup(request):
    """AJAX endpoint para obtener datos del maestro al seleccionarlo en el formulario FUP"""
    from django.http import JsonResponse
    
    maestro_id = request.GET.get('maestro_id')
    if not maestro_id:
        return JsonResponse({'error': 'No se proporcionó ID de maestro'}, status=400)
    
    try:
        maestro = Maestro.objects.get(id_maestro=maestro_id)
        data = {
            'rfc': maestro.rfc or '',
            'curp': maestro.curp or '',
            'techo_financiero': maestro.techo_f or '',
            'clave_presupuestal': maestro.clave_presupuestal or '',
            'nombre_completo': f"{maestro.a_paterno or ''} {maestro.a_materno or ''} {maestro.nombres or ''}".strip()
        }
        return JsonResponse(data)
    except Maestro.DoesNotExist:
        return JsonResponse({'error': 'Maestro no encontrado'}, status=404)
