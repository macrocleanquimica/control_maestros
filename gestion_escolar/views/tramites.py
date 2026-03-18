import os
import json
import re
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, JsonResponse, FileResponse
from django.conf import settings

from ..forms import TramiteForm
from ..models import PlantillaTramite, Historial, MotivoTramite

# Import helpers from the new module
from .helpers import (
    generate_word_document, get_full_name, get_school_info, 
    get_director_info, get_supervisor_info, serialize_form_data,
    calculate_time_difference # Added this import
)

# Vistas para Trámites
@permission_required('gestion_escolar.acceder_tramites', raise_exception=True)
def generar_tramites_generales(request):
    if request.method == 'POST':
        form = TramiteForm(request.POST, form_type='tramites')
        if form.is_valid():
            plantilla_id = form.cleaned_data['plantilla'].id
            plantilla_tramite = PlantillaTramite.objects.get(id=plantilla_id)

            success, message = generate_word_document(form.cleaned_data, plantilla_tramite, request.user)

            if success:
                try:
                    datos_para_historial = form.cleaned_data.copy()
                    maestro_titular_obj = form.cleaned_data.get('maestro_titular')
                    escuela_titular = maestro_titular_obj.id_escuela if maestro_titular_obj else None
                    zona_esc = escuela_titular.zona_esc if escuela_titular else None

                    escuela_info = get_school_info(escuela_titular)
                    director_info = get_director_info(escuela_titular)
                    supervisor_info = get_supervisor_info(zona_esc)

                    datos_para_historial['techo_financiero_titular'] = maestro_titular_obj.techo_f if maestro_titular_obj else ''
                    datos_para_historial['clave_ct'] = escuela_info.get('id_escuela', '')
                    datos_para_historial['nombre_ct'] = escuela_info.get('nombre_ct', '')
                    datos_para_historial['turno'] = escuela_info.get('turno', '')
                    datos_para_historial['domicilio_ct'] = escuela_info.get('domicilio', '')
                    datos_para_historial['z_escolar'] = escuela_info.get('zona_esc_numero', '')
                    datos_para_historial['region'] = escuela_info.get('region', '')
                    datos_para_historial['sostenimiento'] = escuela_info.get('sostenimiento', '')
                    datos_para_historial['supervisor'] = supervisor_info.get('nombre', '')
                    datos_para_historial['director'] = director_info.get('nombre', '')
                    
                    Historial.objects.create(
                        usuario=request.user,
                        tipo_documento=f"Trámite - {plantilla_tramite.nombre}",
                        maestro=maestro_titular_obj,
                        ruta_archivo=message,
                        motivo=form.cleaned_data.get('motivo_tramite').motivo_tramite if form.cleaned_data.get('motivo_tramite') else '',
                        maestro_secundario_nombre=get_full_name(form.cleaned_data.get('maestro_interino')),
                        datos_tramite=serialize_form_data(datos_para_historial)
                    )
                except Exception as e:
                    messages.warning(request, f"Advertencia: El trámite se generó pero no se pudo guardar en el historial: {e}")

                with open(message, 'rb') as doc_file:
                    response = HttpResponse(doc_file.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(message)}"'
                    messages.success(request, 'Trámite generado y descargado correctamente.')
                    return response
            else:
                messages.error(request, f'Error al generar el trámite: {message}')
                return redirect('generar_tramites_generales')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = TramiteForm(form_type='tramites')

    context = {
        'form': form,
        'titulo': 'Generar Trámite'
    }
    return render(request, 'gestion_escolar/generar_tramite.html', context)

@permission_required('gestion_escolar.acceder_oficios', raise_exception=True)
def generar_oficios(request):
    if request.method == 'POST':
        form = TramiteForm(request.POST, form_type='oficios')
        if form.is_valid():
            plantilla_id = form.cleaned_data['plantilla'].id
            plantilla_tramite = PlantillaTramite.objects.get(id=plantilla_id)

            # Preparar los datos para el documento Word
            data_for_document = form.cleaned_data.copy()
            maestro_titular_obj = form.cleaned_data.get('maestro_titular')

            if maestro_titular_obj:
                data_for_document['CURP_TITULAR'] = maestro_titular_obj.curp
                data_for_document['RFC_TITULAR'] = maestro_titular_obj.rfc
                data_for_document['NOMBRE_COMPLETO_TITULAR'] = get_full_name(maestro_titular_obj)
                data_for_document['CLAVE_PRESUPUESTAL_TITULAR'] = maestro_titular_obj.clave_presupuestal
                data_for_document['CODIGO_TITULAR'] = maestro_titular_obj.codigo
                data_for_document['FUNCION_TITULAR'] = maestro_titular_obj.funcion
                data_for_document['CLAVE_TECHO_FINANCIERO_TITULAR'] = maestro_titular_obj.techo_f
                
                if maestro_titular_obj.id_escuela:
                    data_for_document['ZONA_ECONOMICA_TECHO_FINANCIERO_TITULAR'] = maestro_titular_obj.id_escuela.zona_economica
                    data_for_document['SOSTENIMIENTO_TITULAR'] = maestro_titular_obj.id_escuela.sostenimiento
                else:
                    data_for_document['ZONA_ECONOMICA_TECHO_FINANCIERO_TITULAR'] = ''
                    data_for_document['SOSTENIMIENTO_TITULAR'] = ''
            else:
                data_for_document['CURP_TITULAR'] = ''
                data_for_document['RFC_TITULAR'] = ''
                data_for_document['NOMBRE_COMPLETO_TITULAR'] = ''
                data_for_document['CLAVE_PRESUPUESTAL_TITULAR'] = ''
                data_for_document['CODIGO_TITULAR'] = ''
                data_for_document['FUNCION_TITULAR'] = ''
                data_for_document['CLAVE_TECHO_FINANCIERO_TITULAR'] = ''
                data_for_document['ZONA_ECONOMICA_TECHO_FINANCIERO_TITULAR'] = ''
                data_for_document['SOSTENIMIENTO_TITULAR'] = ''

            # Lógica para calcular antigüedad si la plantilla es "CONSTANCIA DE CAMBIO"
            if plantilla_tramite.nombre.upper().strip() == 'CONSTANCIA DE CAMBIO':
                fecha_al_corte = data_for_document.get('fecha_al_corte')
                fecha_del_calculo = data_for_document.get('fecha_del_calculo')

                if fecha_al_corte and fecha_del_calculo:
                    antiguedad = calculate_time_difference(fecha_al_corte, fecha_del_calculo)
                    data_for_document['antiguedad_funcion'] = antiguedad
                    data_for_document['antiguedad_categoria'] = antiguedad
            
            # Sobrescribir el archivo de la plantilla si se seleccionó uno específico
            archivo_especifico = form.cleaned_data.get('archivo_plantilla_especifico')
            if archivo_especifico:
                # Construir la ruta al archivo específico dentro de la carpeta de plantillas
                # Asumimos que están en la misma carpeta que el archivo original de la plantilla
                base_dir = os.path.dirname(plantilla_tramite.ruta_archivo)
                plantilla_tramite.ruta_archivo = os.path.join(base_dir, archivo_especifico)
            
            success, message = generate_word_document(data_for_document, plantilla_tramite, request.user)

            if success:
                try:
                    datos_para_historial = data_for_document.copy()
                    
                    escuela_titular = maestro_titular_obj.id_escuela if maestro_titular_obj else None
                    zona_esc = escuela_titular.zona_esc if escuela_titular else None

                    escuela_info = get_school_info(escuela_titular)
                    director_info = get_director_info(escuela_titular)
                    supervisor_info = get_supervisor_info(zona_esc)

                    datos_para_historial['techo_financiero_titular'] = maestro_titular_obj.techo_f if maestro_titular_obj else ''
                    datos_para_historial['clave_ct'] = escuela_info.get('id_escuela', '')
                    datos_para_historial['nombre_ct'] = escuela_info.get('nombre_ct', '')
                    datos_para_historial['turno'] = escuela_info.get('turno', '')
                    datos_para_historial['domicilio_ct'] = escuela_info.get('domicilio', '')
                    datos_para_historial['z_escolar'] = escuela_info.get('zona_esc_numero', '')
                    datos_para_historial['region'] = escuela_info.get('region', '')
                    datos_para_historial['sostenimiento'] = escuela_info.get('sostenimiento', '')
                    datos_para_historial['supervisor'] = supervisor_info.get('nombre', '')
                    datos_para_historial['director'] = director_info.get('nombre', '')

                    Historial.objects.create(
                        usuario=request.user,
                        tipo_documento=f"Oficio - {plantilla_tramite.nombre}",
                        maestro=maestro_titular_obj,
                        ruta_archivo=message,
                        motivo=form.cleaned_data.get('motivo_tramite').motivo_tramite if form.cleaned_data.get('motivo_tramite') else '',
                        maestro_secundario_nombre=get_full_name(form.cleaned_data.get('maestro_interino')),
                        datos_tramite=serialize_form_data(datos_para_historial)
                    )
                except Exception as e:
                    messages.warning(request, f"Advertencia: El oficio se generó pero no se pudo guardar en el historial: {e}")

                with open(message, 'rb') as doc_file:
                    response = HttpResponse(doc_file.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(message)}"'
                    messages.success(request, 'Oficio generado y descargado correctamente.')
                    return response
            else:
                messages.error(request, f'Error al generar el oficio: {message}')
                return redirect('generar_oficios')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = TramiteForm(form_type='oficios')

    context = {
        'form': form,
        'titulo': 'Generar Oficio'
    }
    return render(request, 'gestion_escolar/generar_tramite.html', context)

@permission_required('gestion_escolar.acceder_historial', raise_exception=True)
def historial(request):
    historial_items = Historial.objects.select_related('usuario', 'maestro').all().order_by('-fecha_creacion')
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
        ct_keys_list = [
            'techo_financiero_titular', 'clave_ct', 'nombre_ct', 'turno', 
            'domicilio_ct', 'z_escolar', 'region', 'sostenimiento', 
            'supervisor', 'director'
        ]

        context = {
            'historial_item': historial_item,
            'datos_tramite': historial_item.datos_tramite,
            'titulo': f'Detalle de {historial_item.tipo_documento}',
            'ct_keys_list': ct_keys_list,
        }
        return render(request, 'gestion_escolar/historial_detalle_tramite.html', context)
    else:
        messages.error(request, "Este registro de historial no contiene datos de trámite/oficio.")
        return redirect('historial')

@login_required
def descargar_archivo_historial(request, item_id):
    item = get_object_or_404(Historial, id=item_id)
    
    file_path = item.ruta_archivo
    if not file_path and item.lote_reporte and item.lote_reporte.archivo_generado:
        file_path = item.lote_reporte.archivo_generado.path

    if not file_path:
        messages.error(request, "No hay archivo para descargar.")
        return redirect('historial')

    if not os.path.abspath(file_path).startswith(os.path.abspath(settings.BASE_DIR)):
        messages.error(request, "Acceso denegado.")
        return redirect('historial')

    if os.path.exists(file_path):
        try:
            return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))
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

@login_required
def corregir_tramite(request, item_id):
    historial_item = get_object_or_404(Historial, id=item_id)
    
    # Validación de seguridad: Solo el autor, superusuario o ADMINISTRATIVO
    es_autor = historial_item.usuario == request.user
    es_admin = request.user.is_superuser or request.user.groups.filter(name='ADMINISTRATIVO').exists()
    
    if not (es_autor or es_admin):
        messages.error(request, "No tienes permiso para corregir este documento. Solo el autor original o un administrador pueden hacerlo.")
        return redirect('historial_detalle_tramite', historial_id=item_id)

    # Determinar el tipo de formulario (tramites u oficios)
    tipo_doc = historial_item.tipo_documento.upper()
    form_type = 'oficios' if 'OFICIO' in tipo_doc else 'tramites'

    if request.method == 'POST':
        form = TramiteForm(request.POST, form_type=form_type)
        if form.is_valid():
            plantilla_id = form.cleaned_data['plantilla'].id
            plantilla_tramite = PlantillaTramite.objects.get(id=plantilla_id)

            # Preparar datos (similar a generar_oficios/generar_tramite)
            data_for_document = form.cleaned_data.copy()
            maestro_titular_obj = form.cleaned_data.get('maestro_titular')

            # Lógica extraída de generar_oficios para Oficios
            if maestro_titular_obj:
                data_for_document['NOMBRE_COMPLETO_TITULAR'] = get_full_name(maestro_titular_obj)
                
                if form_type == 'oficios':
                    data_for_document['CURP_TITULAR'] = maestro_titular_obj.curp
                    data_for_document['RFC_TITULAR'] = maestro_titular_obj.rfc
                    data_for_document['CLAVE_PRESUPUESTAL_TITULAR'] = maestro_titular_obj.clave_presupuestal
                    data_for_document['CODIGO_TITULAR'] = maestro_titular_obj.codigo
                    data_for_document['FUNCION_TITULAR'] = maestro_titular_obj.funcion
                    data_for_document['CLAVE_TECHO_FINANCIERO_TITULAR'] = maestro_titular_obj.techo_f
                
                if maestro_titular_obj.id_escuela:
                    data_for_document['ZONA_ECONOMICA_TECHO_FINANCIERO_TITULAR'] = maestro_titular_obj.id_escuela.zona_economica
                    data_for_document['SOSTENIMIENTO_TITULAR'] = maestro_titular_obj.id_escuela.sostenimiento
                else:
                    data_for_document['ZONA_ECONOMICA_TECHO_FINANCIERO_TITULAR'] = ''
                    data_for_document['SOSTENIMIENTO_TITULAR'] = ''

            # Lógica para calcular antigüedad si aplica
            if plantilla_tramite.nombre.upper().strip() == 'CONSTANCIA DE CAMBIO':
                fecha_al_corte = data_for_document.get('fecha_al_corte')
                fecha_del_calculo = data_for_document.get('fecha_del_calculo')
                if fecha_al_corte and fecha_del_calculo:
                    antiguedad = calculate_time_difference(fecha_al_corte, fecha_del_calculo)
                    data_for_document['antiguedad_funcion'] = antiguedad
                    data_for_document['antiguedad_categoria'] = antiguedad

            # Sobrescribir el archivo de la plantilla si se seleccionó uno específico
            archivo_especifico = form.cleaned_data.get('archivo_plantilla_especifico')
            if archivo_especifico:
                base_dir = os.path.dirname(plantilla_tramite.ruta_archivo)
                plantilla_tramite.ruta_archivo = os.path.join(base_dir, archivo_especifico)

            # Generar el nuevo documento
            success, message = generate_word_document(data_for_document, plantilla_tramite, request.user)

            if success:
                # Eliminar el archivo anterior si existe
                if historial_item.ruta_archivo and os.path.exists(historial_item.ruta_archivo):
                    try:
                        os.remove(historial_item.ruta_archivo)
                    except Exception as e:
                        print(f"No se pudo eliminar el archivo anterior: {e}")

                # Actualizar Historial
                try:
                    datos_para_historial = data_for_document.copy()
                    escuela_titular = maestro_titular_obj.id_escuela if maestro_titular_obj else None
                    zona_esc = escuela_titular.zona_esc if escuela_titular else None

                    escuela_info = get_school_info(escuela_titular)
                    director_info = get_director_info(escuela_titular)
                    supervisor_info = get_supervisor_info(zona_esc)

                    datos_para_historial['techo_financiero_titular'] = maestro_titular_obj.techo_f if maestro_titular_obj else ''
                    datos_para_historial['clave_ct'] = escuela_info.get('id_escuela', '')
                    datos_para_historial['nombre_ct'] = escuela_info.get('nombre_ct', '')
                    datos_para_historial['turno'] = escuela_info.get('turno', '')
                    datos_para_historial['domicilio_ct'] = escuela_info.get('domicilio', '')
                    datos_para_historial['z_escolar'] = escuela_info.get('zona_esc_numero', '')
                    datos_para_historial['region'] = escuela_info.get('region', '')
                    datos_para_historial['sostenimiento'] = escuela_info.get('sostenimiento', '')
                    datos_para_historial['supervisor'] = supervisor_info.get('nombre', '')
                    datos_para_historial['director'] = director_info.get('nombre', '')

                    historial_item.tipo_documento = f"{'Oficio' if form_type == 'oficios' else 'Trámite'} - {plantilla_tramite.nombre}"
                    historial_item.maestro = maestro_titular_obj
                    historial_item.ruta_archivo = message
                    historial_item.motivo = form.cleaned_data.get('motivo_tramite').motivo_tramite if form.cleaned_data.get('motivo_tramite') else ''
                    historial_item.maestro_secundario_nombre = get_full_name(form.cleaned_data.get('maestro_interino'))
                    historial_item.datos_tramite = serialize_form_data(datos_para_historial)
                    historial_item.save()

                    messages.success(request, 'Documento corregido y regenerado correctamente.')
                except Exception as e:
                    messages.warning(request, f"Advertencia: El documento se generó pero hubo un error al actualizar el historial: {e}")

                with open(message, 'rb') as doc_file:
                    response = HttpResponse(doc_file.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(message)}"'
                    return response
            else:
                messages.error(request, f'Error al regenerar el documento: {message}')
        else:
            # Reportar errores específicos de campos para diagnóstico
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields else field
                messages.error(request, f"Error en '{field_label}': {errors[0]}")
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        # Pre-poblar el formulario con los datos guardados
        initial_data = historial_item.datos_tramite.copy() if historial_item.datos_tramite else {}
        
        # Convertir fechas de ISO string a objetos date para el formulario
        for key, value in initial_data.items():
            if isinstance(value, str) and re.match(r'^\d{4}-\d{2}-\d{2}', value):
                try:
                    initial_data[key] = date.fromisoformat(value[:10])
                except:
                    pass
        
        from gestion_escolar.models import Maestro
        titular_id = historial_item.maestro.id_maestro if historial_item.maestro else None
        interino_id = initial_data.get('maestro_interino')

        if titular_id:
            try:
                maestro_titular = Maestro.objects.get(id_maestro=titular_id)
                initial_data['maestro_titular'] = titular_id
                initial_data['nombre_titular_display'] = get_full_name(maestro_titular)
                initial_data['curp_titular_display'] = maestro_titular.curp
                initial_data['rfc_titular_display'] = maestro_titular.rfc
                initial_data['clave_presupuestal_titular_display'] = maestro_titular.clave_presupuestal
                initial_data['categoria_titular_display'] = maestro_titular.categog.descripcion if maestro_titular.categog else ''
                initial_data['funcion_titular_display'] = maestro_titular.funcion
                initial_data['incentivos'] = ", ".join([i.codigo for i in maestro_titular.incentivos.all()]) if hasattr(maestro_titular, 'incentivos') else ''
            except Maestro.DoesNotExist:
                pass

        if interino_id:
            try:
                maestro_interino = Maestro.objects.get(id_maestro=interino_id)
                initial_data['maestro_interino'] = interino_id
                initial_data['nombre_interino_display'] = get_full_name(maestro_interino)
                initial_data['curp_interino_display'] = maestro_interino.curp
                initial_data['rfc_interino_display'] = maestro_interino.rfc
            except Maestro.DoesNotExist:
                pass
        
        form = TramiteForm(initial=initial_data, form_type=form_type)

    context = {
        'form': form,
        'titulo': f'Corregir {historial_item.tipo_documento}',
        'historial_item': historial_item,
        'is_edit': True
    }
    return render(request, 'gestion_escolar/generar_tramite.html', context)
