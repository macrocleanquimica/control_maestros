import os
import json
import re
from datetime import date
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, JsonResponse, FileResponse
from django.conf import settings
from django.urls import reverse

from ..forms import TramiteForm
from ..models import PlantillaTramite, Historial, MotivoTramite, Maestro, Escuela, Interinato, Vacancia
from .helpers import vacancia_de_historial, vacancias_candidatas_historial


def _contexto_configuracion_plantillas(form):
    """Datos que el formulario de generación usa para mostrarse dinámicamente."""
    from ..campos_plantilla import configuraciones_para_js, plantillas_sin_motivo_js
    from ..plantillas_utils import json_para_js

    queryset = PlantillaTramite.objects.filter(activa=True)
    return {
        'configuraciones_json': json_para_js(configuraciones_para_js(queryset)),
        'plantillas_sin_motivo_json': json_para_js(plantillas_sin_motivo_js(queryset)),
        'campos_personalizados': getattr(form, 'campos_personalizados', []),
        'plantilla_seleccionada': getattr(form, 'plantilla_seleccionada', None),
        'configuracion_plantilla': getattr(form, 'configuracion_plantilla', {}),
    }

# Trámites cuyo motivo de movimiento es fijo: el formulario lo oculta y aquí se
# fuerza, para que el motivo quede grabado en el historial sin que el usuario lo elija.
MOTIVOS_FIJOS = {
    'ALTA PROVISIONAL EN VACANTE DEFINITIVA (99)': 'ALTA PROVISIONAL EN VACANTE DEFINITIVA (99)',
}


def _forzar_motivo_fijo(plantilla_nombre, datos):
    """Fija el motivo cuando la plantilla lo tiene predetermined.

    Devuelve el nombre del motivo aplicado, o None si la plantilla no lo tiene.
    """
    motivo_texto = MOTIVOS_FIJOS.get((plantilla_nombre or '').strip().upper())
    if not motivo_texto:
        return None

    motivo_obj = MotivoTramite.objects.filter(motivo_tramite=motivo_texto).first()
    datos['motivo_tramite'] = motivo_obj
    return motivo_texto

# Import helpers from the new module
from .helpers import (
    generate_word_document, get_full_name, get_school_info, 
    get_director_info, get_supervisor_info, serialize_form_data,
    calculate_time_difference, resolver_ruta_plantilla, # Added this import
    PLANTILLAS_WORD_DIR,
)

# Vistas para Trámites
@permission_required('gestion_escolar.acceder_tramites', raise_exception=True)
def generar_tramites_generales(request):
    if request.method == 'POST':
        form = TramiteForm(request.POST, form_type='tramites')
        if form.is_valid():
            plantilla_id = form.cleaned_data['plantilla'].id
            plantilla_tramite = PlantillaTramite.objects.get(id=plantilla_id)

            # El motivo va fijado ANTES de generar el documento para que
            # T_Movimiento salga con el valor correcto en el .docx.
            _forzar_motivo_fijo(plantilla_tramite.nombre, form.cleaned_data)

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
        plantilla_id = request.GET.get('plantilla')
        initial = {'plantilla': plantilla_id} if plantilla_id else None
        form = TramiteForm(initial=initial, form_type='tramites', plantilla_id=plantilla_id)

    context = {
        'form': form,
        'titulo': 'Generar Trámite'
    }
    context.update(_contexto_configuracion_plantillas(form))
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

            # Lógica para "SOLICITUD BECA COMISION"
            if plantilla_tramite.nombre.upper().strip() == 'SOLICITUD BECA COMISION':
                fecha_al_corte = data_for_document.get('fecha_al_corte')
                fecha_del_calculo = data_for_document.get('fecha_del_calculo')

                if fecha_al_corte and fecha_del_calculo:
                    antiguedad = calculate_time_difference(fecha_al_corte, fecha_del_calculo)
                    data_for_document['antiguedad_funcion'] = antiguedad
              # Lógica para "PRESENTACION LABORAL PARA CAMBIO DE ADSCRIPCION"
            if plantilla_tramite.nombre.upper().strip() == 'PRESENTACION LABORAL PARA CAMBIO DE ADSCRIPCION':
                tipo_cambio = form.cleaned_data.get('tipo_cambio')
                maestro_sustituido_obj = form.cleaned_data.get('maestro_sustituido')
                escuela_destino_obj = form.cleaned_data.get('escuela_destino')
                if tipo_cambio and tipo_cambio.upper() == 'SUSTITUCION' and maestro_sustituido_obj:
                    escuela_destino_final = maestro_sustituido_obj.id_escuela
                    techo_f_destino = escuela_destino_final.id_escuela if escuela_destino_final else None
                    data_for_document['sustituida_nombre'] = get_full_name(maestro_sustituido_obj)
                elif tipo_cambio and tipo_cambio.upper() == 'INCREMENTO' and escuela_destino_obj:
                    escuela_destino_final = escuela_destino_obj
                    techo_f_destino = escuela_destino_final.id_escuela
                    data_for_document['sustituida_nombre'] = ''
                else:
                    escuela_destino_final = None
                    techo_f_destino = None

                data_for_document['_dest_escuela'] = escuela_destino_final
                if escuela_destino_final and maestro_titular_obj:
                    escuela_ant = maestro_titular_obj.id_escuela
                    data_for_document['escuela_anterior_id'] = escuela_ant.id if escuela_ant else None
                    data_for_document['escuela_anterior_cct'] = escuela_ant.id_escuela if escuela_ant else ''
                    data_for_document['escuela_anterior_nombre'] = escuela_ant.nombre_ct if escuela_ant else ''
                    data_for_document['techo_f_anterior'] = maestro_titular_obj.techo_f or ''

                    maestro_titular_obj.id_escuela = escuela_destino_final
                    maestro_titular_obj.techo_f = techo_f_destino
                    maestro_titular_obj.save()

            # Lógica para "JUSTIFICACION DE RETROACTIVIDAD"
            if plantilla_tramite.nombre.upper().strip() == 'JUSTIFICACION DE RETROACTIVIDAD':
                razon = (form.cleaned_data.get('opcionjustificacion', '') or form.cleaned_data.get('razon_retroactividad', '') or '').lower()
                fecha_usicamm = form.cleaned_data.get('fecha_usicamm')
                texto_otro = form.cleaned_data.get('texto_razon_otro', '')

                meses_nombre = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                if razon == 'firmas':
                    razon_texto = 'los tiempos que implicó la recabación de las firmas correspondientes'
                    fecha_usicamm_letra = ''
                elif razon == 'presentacion':
                    razon_texto = 'que el maestro se presentó en esta fecha con su asignación'
                    fecha_usicamm_letra = ''
                elif razon == 'usicamm':
                    razon_texto = 'que USICAMM asignó con la siguiente fecha: '
                    if fecha_usicamm:
                        fecha_usicamm_letra = f"{fecha_usicamm.day} de {meses_nombre[fecha_usicamm.month - 1]} de {fecha_usicamm.year}"
                    else:
                        fecha_usicamm_letra = ''
                elif razon == 'otro':
                    razon_texto = (texto_otro or '').strip()
                    fecha_usicamm_letra = ''
                else:
                    razon_texto = razon or ''
                    fecha_usicamm_letra = ''

                data_for_document['opcionjustificacion'] = razon_texto
                data_for_document['Razon_Retroactividad'] = razon_texto
                data_for_document['Fecha_USICAMM_Letra'] = fecha_usicamm_letra
                data_for_document['fecha_usicamm_letra'] = fecha_usicamm_letra
                data_for_document['Fecha_USICAMM'] = fecha_usicamm.strftime('%d/%m/%Y') if fecha_usicamm else ''
                data_for_document['fecha_usicamm'] = fecha_usicamm.strftime('%d/%m/%Y') if fecha_usicamm else ''
                interino_obj = form.cleaned_data.get('maestro_interino')
                if interino_obj:
                    data_for_document['Nombre_Interino'] = get_full_name(interino_obj)
                    data_for_document['Nombre_Interino_Retro'] = get_full_name(interino_obj)

            # Sobrescribir el archivo de la plantilla si se seleccionó uno específico
            archivo_especifico = form.cleaned_data.get('archivo_plantilla_especifico')
            if archivo_especifico:
                # Construir la ruta al archivo específico dentro de la carpeta canónica
                # (antes asumía la carpeta del registro, que podía ser la raíz legacy o un C:\\ absoluto).
                resuelta = resolver_ruta_plantilla(plantilla_tramite.ruta_archivo)
                base_dir = os.path.dirname(resuelta) if resuelta else PLANTILLAS_WORD_DIR
                plantilla_tramite.ruta_archivo = os.path.join(base_dir, archivo_especifico)
            
            success, message = generate_word_document(data_for_document, plantilla_tramite, request.user)

            if success:
                try:
                    datos_para_historial = data_for_document.copy()
                    
                    maestro_para_historial = maestro_titular_obj or form.cleaned_data.get('maestro_interino')
                    escuela_titular = maestro_para_historial.id_escuela if maestro_para_historial else None
                    zona_esc = escuela_titular.zona_esc if escuela_titular else None

                    escuela_info = get_school_info(escuela_titular)
                    director_info = get_director_info(escuela_titular)
                    supervisor_info = get_supervisor_info(zona_esc)

                    datos_para_historial['techo_financiero_titular'] = maestro_para_historial.techo_f if maestro_para_historial else ''
                    datos_para_historial['clave_ct'] = escuela_info.get('id_escuela', '')
                    datos_para_historial['nombre_ct'] = escuela_info.get('nombre_ct', '')
                    datos_para_historial['turno'] = escuela_info.get('turno', '')
                    datos_para_historial['domicilio_ct'] = escuela_info.get('domicilio', '')
                    datos_para_historial['z_escolar'] = escuela_info.get('zona_esc_numero', '')
                    datos_para_historial['region'] = escuela_info.get('region', '')
                    datos_para_historial['sostenimiento'] = escuela_info.get('sostenimiento', '')
                    datos_para_historial['supervisor'] = supervisor_info.get('nombre', '')
                    datos_para_historial['director'] = director_info.get('nombre', '')
                    if 'escuela_anterior_id' in data_for_document:
                        datos_para_historial['escuela_anterior_id'] = data_for_document.get('escuela_anterior_id')
                        datos_para_historial['escuela_anterior_cct'] = data_for_document.get('escuela_anterior_cct')
                        datos_para_historial['escuela_anterior_nombre'] = data_for_document.get('escuela_anterior_nombre')
                        datos_para_historial['techo_f_anterior'] = data_for_document.get('techo_f_anterior')

                    historial_motivo = form.cleaned_data.get('motivo_tramite')
                    historial_motivo_text = historial_motivo.motivo_tramite if historial_motivo else ''
                    if plantilla_tramite.nombre.upper().strip() in ['PRESENTACION LABORAL PARA CAMBIO DE ADSCRIPCION', 'JUSTIFICACION DE RETROACTIVIDAD']:
                        historial_motivo_text = ''

                    Historial.objects.create(
                        usuario=request.user,
                        tipo_documento=f"Oficio - {plantilla_tramite.nombre}",
                        maestro=maestro_para_historial,
                        ruta_archivo=message,
                        motivo=historial_motivo_text,
                        observaciones=data_for_document.get('observaciones', ''),
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
        plantilla_id = request.GET.get('plantilla')
        initial = {'plantilla': plantilla_id} if plantilla_id else None
        form = TramiteForm(initial=initial, form_type='oficios', plantilla_id=plantilla_id)

    context = {
        'form': form,
        'titulo': 'Generar Oficio'
    }
    context.update(_contexto_configuracion_plantillas(form))
    return render(request, 'gestion_escolar/generar_tramite.html', context)

@permission_required('gestion_escolar.acceder_historial', raise_exception=True)
def historial(request):
    historial_items = Historial.objects.select_related('usuario', 'maestro', 'usuario_cancelacion').all().order_by('-fecha_creacion')
    escuelas = Escuela.objects.all().order_by('id_escuela')
    context = {
        'historial_items': historial_items,
        'escuelas': escuelas,
        'titulo': 'Historial de Documentos'
    }
    return render(request, 'gestion_escolar/historial.html', context)

@login_required
@permission_required('gestion_escolar.acceder_historial', raise_exception=True)
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
@permission_required('gestion_escolar.acceder_historial', raise_exception=True)
def historial_detalle_tramite(request, historial_id):
    historial_item = get_object_or_404(Historial, id=historial_id)
    ct_keys_list = [
        'techo_financiero_titular', 'clave_ct', 'nombre_ct', 'turno',
        'domicilio_ct', 'z_escolar', 'region', 'sostenimiento',
        'supervisor', 'director'
    ]
    datos_tramite = historial_item.datos_tramite or {}
    tipo_documento = (historial_item.tipo_documento or '').strip()
    es_tramite = tipo_documento.startswith('Trámite -') or tipo_documento.startswith('Oficio -')
    tiene_archivo = bool(historial_item.ruta_archivo) or bool(
        historial_item.lote_reporte and historial_item.lote_reporte.archivo_generado
    )

    volver_url = reverse('historial')
    volver_label = 'Volver'
    if request.GET.get('from') == 'kardex' and historial_item.maestro_id:
        volver_url = reverse('kardex_maestro_detail', args=[historial_item.maestro_id])
        volver_label = 'Volver al kardex'

    vacancia_relacionada = vacancia_de_historial(historial_item)
    puede_corregir = False
    if historial_item.estado != 'CANCELADO' and vacancias_candidatas_historial(historial_item).exists():
        es_autor = historial_item.usuario_id == request.user.id
        es_admin = request.user.is_superuser or request.user.groups.filter(name='ADMINISTRADOR').exists()
        puede_corregir = (es_autor or es_admin) and request.user.has_perm('gestion_escolar.change_vacancia')

    corregir_url = reverse('corregir_vacancia_historial', args=[historial_item.id])
    if request.GET.get('from') == 'kardex':
        corregir_url += '?from=kardex'

    escuelas = Escuela.objects.all().order_by('id_escuela')

    context = {
        'historial_item': historial_item,
        'datos_tramite': datos_tramite,
        'titulo': f'Detalle de {historial_item.tipo_documento}',
        'ct_keys_list': ct_keys_list,
        'es_tramite': es_tramite,
        'tiene_archivo': tiene_archivo,
        'volver_url': volver_url,
        'volver_label': volver_label,
        'vacancia_relacionada': vacancia_relacionada,
        'puede_corregir': puede_corregir,
        'corregir_url': corregir_url,
        'escuelas': escuelas,
    }
    return render(request, 'gestion_escolar/historial_detalle_tramite.html', context)

@login_required
@permission_required('gestion_escolar.acceder_historial', raise_exception=True)
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
@permission_required('gestion_escolar.delete_historial', raise_exception=True)
def eliminar_historial_item(request, item_id):
    if request.method == 'POST':
        # Validación de seguridad: solo superusuarios o miembros del grupo ADMINISTRADOR
        es_admin = request.user.is_superuser or request.user.groups.filter(name='ADMINISTRADOR').exists()
        if not es_admin:
            return JsonResponse({'status': 'error', 'message': 'Solo los administradores pueden eliminar registros definitivamente.'}, status=403)
        item = get_object_or_404(Historial, id=item_id)
        try:
            item.delete()
            return JsonResponse({'status': 'success', 'message': 'Registro eliminado correctamente.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)

@login_required
@permission_required('gestion_escolar.change_historial', raise_exception=True)
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
@permission_required('gestion_escolar.change_historial', raise_exception=True)
def info_cancelar_tramite(request, item_id):
    """Devuelve metadatos para preparar la ventana modal de cancelación."""
    historial_item = get_object_or_404(Historial, id=item_id)
    datos = historial_item.datos_tramite or {}
    tipo = historial_item.tipo_documento or ''
    es_cambio_adscripcion = 'CAMBIO DE ADSCRIPCION' in tipo.upper() or 'CAMBIO DE ADSCRIPCIÓN' in tipo.upper()
    escuela_ant_cct = datos.get('escuela_anterior_cct') or ''
    escuela_ant_nombre = datos.get('escuela_anterior_nombre') or ''

    vacancia = vacancia_de_historial(historial_item)
    tiene_interinato = False
    if vacancia and Interinato.objects.filter(vacancia=vacancia, estatus='ACTIVO').exists():
        tiene_interinato = True
    elif historial_item.maestro and Interinato.objects.filter(maestro_titular=historial_item.maestro, estatus='ACTIVO').exists():
        tiene_interinato = True

    return JsonResponse({
        'status': 'success',
        'id': historial_item.id,
        'tipo_documento': tipo,
        'maestro': str(historial_item.maestro) if historial_item.maestro else 'N/A',
        'estado': historial_item.estado,
        'es_cambio_adscripcion': es_cambio_adscripcion,
        'escuela_anterior_cct': escuela_ant_cct,
        'escuela_anterior_nombre': escuela_ant_nombre,
        'escuela_anterior_id': datos.get('escuela_anterior_id'),
        'tiene_interinato': tiene_interinato,
    })


@login_required
@permission_required('gestion_escolar.change_historial', raise_exception=True)
def cancelar_tramite(request, item_id):
    """Cancela un trámite u oficio, revierte afectaciones y libera plazas/interinatos."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)

    historial_item = get_object_or_404(Historial, id=item_id)

    # Validación de seguridad: autor original, superusuario o ADMINISTRADOR
    es_autor = historial_item.usuario == request.user
    es_admin = request.user.is_superuser or request.user.groups.filter(name='ADMINISTRADOR').exists()
    if not (es_autor or es_admin):
        return JsonResponse({'status': 'error', 'message': 'No tienes permiso para cancelar este documento. Solo el autor original o un administrador pueden hacerlo.'}, status=403)

    if historial_item.estado == 'CANCELADO':
        return JsonResponse({'status': 'error', 'message': 'El trámite ya se encuentra cancelado.'}, status=400)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    motivo = (data.get('motivo_cancelacion') or '').strip()
    if not motivo:
        return JsonResponse({'status': 'error', 'message': 'Debes especificar el motivo de la cancelación.'}, status=400)

    # 1. Marcar el registro como cancelado
    historial_item.estado = 'CANCELADO'
    historial_item.motivo_cancelacion = motivo
    historial_item.fecha_cancelacion = timezone.now()
    historial_item.usuario_cancelacion = request.user
    historial_item.save()

    detalles_reversion = []

    # 2. Revertir adscripción del maestro si fue un cambio de adscripción
    tipo_doc_upper = (historial_item.tipo_documento or '').upper()
    if 'CAMBIO DE ADSCRIPCION' in tipo_doc_upper or 'CAMBIO DE ADSCRIPCIÓN' in tipo_doc_upper:
        maestro = historial_item.maestro
        if maestro:
            datos = historial_item.datos_tramite or {}
            escuela_ant_id = datos.get('escuela_anterior_id')
            techo_ant = datos.get('techo_f_anterior')
            escuela_manual_id = data.get('escuela_reversion_id')

            escuela_destino = None
            if escuela_manual_id:
                escuela_destino = Escuela.objects.filter(id=escuela_manual_id).first()
            elif escuela_ant_id:
                escuela_destino = Escuela.objects.filter(id=escuela_ant_id).first()

            if escuela_destino:
                maestro.id_escuela = escuela_destino
                maestro.techo_f = techo_ant if (techo_ant and not escuela_manual_id) else escuela_destino.id_escuela
                maestro.save()
                detalles_reversion.append(f"Adscripción de {maestro} revertida a {escuela_destino.id_escuela} - {escuela_destino.nombre_ct}")

    # 3. Invalidar o liberar interinatos / vacancias asociadas
    vacancia = vacancia_de_historial(historial_item)
    if vacancia:
        # Interinatos asociados a la vacancia
        interinatos = Interinato.objects.filter(vacancia=vacancia, estatus='ACTIVO')
        count_inter = 0
        for inter in interinatos:
            inter.estatus = 'CANCELADO'
            nota = f"[Cancelado por trámite #{historial_item.id}: {motivo}]"
            inter.observaciones = f"{inter.observaciones or ''} {nota}".strip()
            inter.save()
            count_inter += 1
        if count_inter > 0:
            detalles_reversion.append(f"{count_inter} interinato(s) marcado(s) como CANCELADO")

        # Si la vacancia tenía asignado un interino, liberarla
        if vacancia.maestro_interino:
            interino_txt = str(vacancia.maestro_interino)
            vacancia.maestro_interino = None
            vacancia.nombre_interino = None
            vacancia.curp_interino = None
            vacancia.save()
            detalles_reversion.append(f"Plaza vacante liberada (se desvinculó al interino {interino_txt})")
    elif historial_item.maestro:
        # Si no hubo vacancia directa pero hay interinatos activos ligados al maestro como titular
        interinatos = Interinato.objects.filter(maestro_titular=historial_item.maestro, estatus='ACTIVO')
        if historial_item.maestro_secundario_nombre:
            nombre_sec = historial_item.maestro_secundario_nombre.strip().upper()
            interinatos_match = [
                i for i in interinatos 
                if i.maestro_interino and (i.maestro_interino.nombre_visible.upper() in nombre_sec or nombre_sec in i.maestro_interino.nombre_visible.upper())
            ]
            for inter in interinatos_match:
                inter.estatus = 'CANCELADO'
                nota = f"[Cancelado por trámite #{historial_item.id}: {motivo}]"
                inter.observaciones = f"{inter.observaciones or ''} {nota}".strip()
                inter.save()
            if interinatos_match:
                detalles_reversion.append(f"{len(interinatos_match)} interinato(s) asociado(s) cancelado(s)")

    msg = "Trámite cancelado exitosamente."
    if detalles_reversion:
        msg += " " + ". ".join(detalles_reversion) + "."

    return JsonResponse({
        'status': 'success',
        'message': msg,
        'estado': 'CANCELADO',
        'fecha_cancelacion': historial_item.fecha_cancelacion.strftime('%d/%m/%Y %H:%M'),
        'motivo_cancelacion': historial_item.motivo_cancelacion,
        'usuario_cancelacion': request.user.username,
        'detalles_reversion': detalles_reversion
    })


@login_required
def corregir_tramite(request, item_id):
    historial_item = get_object_or_404(Historial, id=item_id)

    if historial_item.estado == 'CANCELADO':
        messages.error(request, "No es posible corregir ni regenerar un trámite cancelado.")
        return redirect('historial_detalle_tramite', historial_id=item_id)
    
    # Validación de seguridad: Solo el autor, superusuario o ADMINISTRADOR
    es_autor = historial_item.usuario == request.user
    es_admin = request.user.is_superuser or request.user.groups.filter(name='ADMINISTRADOR').exists()
    
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

            # Lógica para "JUSTIFICACION DE RETROACTIVIDAD"
            if plantilla_tramite.nombre.upper().strip() == 'JUSTIFICACION DE RETROACTIVIDAD':
                razon = (form.cleaned_data.get('opcionjustificacion', '') or form.cleaned_data.get('razon_retroactividad', '') or '').lower()
                fecha_usicamm = form.cleaned_data.get('fecha_usicamm')
                texto_otro = form.cleaned_data.get('texto_razon_otro', '')

                meses_nombre = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                if razon == 'firmas':
                    razon_texto = 'los tiempos que implicó la recabación de las firmas correspondientes'
                    fecha_usicamm_letra = ''
                elif razon == 'presentacion':
                    razon_texto = 'que el maestro se presentó en esta fecha con su asignación'
                    fecha_usicamm_letra = ''
                elif razon == 'usicamm':
                    razon_texto = 'que USICAMM asignó con la siguiente fecha: '
                    if fecha_usicamm:
                        fecha_usicamm_letra = f"{fecha_usicamm.day} de {meses_nombre[fecha_usicamm.month - 1]} de {fecha_usicamm.year}"
                    else:
                        fecha_usicamm_letra = ''
                elif razon == 'otro':
                    razon_texto = (texto_otro or '').strip()
                    fecha_usicamm_letra = ''
                else:
                    razon_texto = razon or ''
                    fecha_usicamm_letra = ''

                data_for_document['opcionjustificacion'] = razon_texto
                data_for_document['Razon_Retroactividad'] = razon_texto
                data_for_document['Fecha_USICAMM_Letra'] = fecha_usicamm_letra
                data_for_document['fecha_usicamm_letra'] = fecha_usicamm_letra
                data_for_document['Fecha_USICAMM'] = fecha_usicamm.strftime('%d/%m/%Y') if fecha_usicamm else ''
                data_for_document['fecha_usicamm'] = fecha_usicamm.strftime('%d/%m/%Y') if fecha_usicamm else ''
                interino_obj = form.cleaned_data.get('maestro_interino')
                if interino_obj:
                    data_for_document['Nombre_Interino'] = get_full_name(interino_obj)
                    data_for_document['Nombre_Interino_Retro'] = get_full_name(interino_obj)

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
                resuelta = resolver_ruta_plantilla(plantilla_tramite.ruta_archivo)
                base_dir = os.path.dirname(resuelta) if resuelta else PLANTILLAS_WORD_DIR
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
                    if 'escuela_anterior_id' in data_for_document:
                        datos_para_historial['escuela_anterior_id'] = data_for_document.get('escuela_anterior_id')
                        datos_para_historial['escuela_anterior_cct'] = data_for_document.get('escuela_anterior_cct')
                        datos_para_historial['escuela_anterior_nombre'] = data_for_document.get('escuela_anterior_nombre')
                        datos_para_historial['techo_f_anterior'] = data_for_document.get('techo_f_anterior')

                    maestro_para_historial = maestro_titular_obj or form.cleaned_data.get('maestro_interino')
                    historial_item.tipo_documento = f"{'Oficio' if form_type == 'oficios' else 'Trámite'} - {plantilla_tramite.nombre}"
                    historial_item.maestro = maestro_para_historial
                    historial_item.ruta_archivo = message
                    historial_item.motivo = form.cleaned_data.get('motivo_tramite').motivo_tramite if form.cleaned_data.get('motivo_tramite') else ''
                    historial_item.maestro_secundario_nombre = get_full_name(form.cleaned_data.get('maestro_interino'))
                    historial_item.datos_tramite = serialize_form_data(datos_para_historial)
                    historial_item.save()

                    messages.success(request, 'Documento corregido y regenerado correctamente.')
                except Exception as e:
                    messages.warning(request, f"Advertencia: El documento se generó pero hubo un error al actualizar el historial: {e}")

                respuesta = redirect('historial_detalle_tramite', historial_id=item_id)
                respuesta['Location'] += '?descargar=1'
                return respuesta
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
    context.update(_contexto_configuracion_plantillas(form))
    return render(request, 'gestion_escolar/generar_tramite.html', context)
