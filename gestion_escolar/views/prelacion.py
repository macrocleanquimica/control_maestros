from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse
import pandas as pd
from io import BytesIO

from ..models import Prelacion, Maestro


@login_required
@permission_required('gestion_escolar.acceder_prelacion', raise_exception=True)
def lista_prelacion(request):
    """Vista principal para mostrar la lista de prelación"""
    return render(request, 'gestion_escolar/lista_prelacion.html', {
        'titulo': 'Lista de Prelación'
    })


@login_required
@permission_required('gestion_escolar.acceder_prelacion', raise_exception=True)
def lista_prelacion_ajax(request):
    """Vista AJAX para DataTables con vinculación a maestros existentes"""
    draw = int(request.GET.get('draw', 0))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    # Configurar ordenamiento
    order_column_index = int(request.GET.get('order[0][column]', 0))
    order_dir = request.GET.get('order[0][dir]', 'asc')
    column_names = ['pos_orden', 'folio', 'curp', 'nombre', 'tipo_val']
    order_column = column_names[order_column_index]
    if order_dir == 'desc':
        order_column = f'-{order_column}'

    # Obtener todos los registros
    queryset = Prelacion.objects.all()
    records_total = queryset.count()

    # Aplicar búsqueda
    if search_value:
        queryset = queryset.filter(
            Q(nombre__icontains=search_value) |
            Q(curp__icontains=search_value) |
            Q(folio__icontains=search_value) |
            Q(pos_orden__icontains=search_value) |
            Q(tipo_val__icontains=search_value)
        )

    records_filtered = queryset.count()
    queryset = queryset.order_by(order_column)[start:start + length]

    # Preparar datos con vinculación a maestros
    data = []
    for registro in queryset:
        # Verificar si existe un maestro con esta CURP
        maestro_existente = None
        if registro.curp:
            maestro_existente = Maestro.objects.filter(curp=registro.curp).first()

        # Crear badge de estado
        if maestro_existente:
            estado_html = f'<span class="badge bg-soft-success text-success border px-2">En Sistema</span>'
            nombre_html = f'<a href="{reverse("detalle_maestro", args=[maestro_existente.id_maestro])}" class="text-primary fw-bold" title="Ver perfil del maestro">{registro.nombre}</a>'
        else:
            estado_html = f'<span class="badge bg-soft-secondary text-secondary border px-2">No Registrado</span>'
            nombre_html = f'<span class="text-dark">{registro.nombre}</span>'

        data.append([
            registro.pos_orden,
            registro.folio,
            registro.curp,
            nombre_html,
            registro.tipo_val,
            estado_html
        ])

    response = {
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
    }
    return JsonResponse(response)


@login_required
@permission_required('gestion_escolar.acceder_prelacion', raise_exception=True)
def importar_prelacion_excel(request):
    """Vista para importar lista anual de prelación desde Excel"""
    if request.method == 'POST':
        if 'archivo_excel' not in request.FILES:
            messages.error(request, 'No se seleccionó ningún archivo.')
            return redirect('importar_prelacion_excel')

        archivo = request.FILES['archivo_excel']
        
        # Validar extensión del archivo
        if not archivo.name.endswith(('.xlsx', '.xls')):
            messages.error(request, 'El archivo debe ser un archivo Excel (.xlsx o .xls)')
            return redirect('importar_prelacion_excel')

        try:
            # Leer el archivo Excel
            df = pd.read_excel(BytesIO(archivo.read()))
            
            # Validar columnas requeridas
            columnas_requeridas = ['pos_orden', 'folio', 'curp', 'nombre', 'tipo_val']
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            
            if columnas_faltantes:
                messages.error(
                    request, 
                    f'El archivo Excel debe contener las siguientes columnas: {", ".join(columnas_requeridas)}. '
                    f'Faltan: {", ".join(columnas_faltantes)}'
                )
                return redirect('importar_prelacion_excel')

            # Eliminar todos los registros anteriores
            registros_eliminados = Prelacion.objects.all().count()
            Prelacion.objects.all().delete()

            # Importar nuevos registros
            registros_importados = 0
            errores = []

            for index, row in df.iterrows():
                try:
                    Prelacion.objects.create(
                        pos_orden=int(row['pos_orden']),
                        folio=str(row['folio']),
                        curp=str(row['curp']),
                        nombre=str(row['nombre']),
                        tipo_val=str(row['tipo_val'])
                    )
                    registros_importados += 1
                except Exception as e:
                    errores.append(f'Fila {index + 2}: {str(e)}')

            # Mostrar resumen
            if registros_importados > 0:
                messages.success(
                    request,
                    f'Importación exitosa: {registros_importados} registros importados. '
                    f'{registros_eliminados} registros anteriores eliminados.'
                )
            
            if errores:
                messages.warning(
                    request,
                    f'Se encontraron {len(errores)} errores durante la importación. '
                    f'Primeros errores: {"; ".join(errores[:5])}'
                )

            return redirect('lista_prelacion')

        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {str(e)}')
            return redirect('importar_prelacion_excel')

    return render(request, 'gestion_escolar/importar_prelacion.html', {
        'titulo': 'Importar Lista de Prelación'
    })
