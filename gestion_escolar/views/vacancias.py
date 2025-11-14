import os
import openpyxl
from datetime import datetime, date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.db import transaction
from django.urls import reverse
from django.conf import settings

from ..models import LoteReporteVacancia, Vacancia, Prelacion, MotivoTramite, PlantillaTramite, Historial
from ..forms import VacanciaForm

from .helpers import get_month_diff, get_full_name, send_to_google_sheet, generate_word_document, serialize_form_data, format_date_for_solicitud_asignacion

@permission_required('gestion_escolar.acceder_vacancias', raise_exception=True)
def gestionar_lote_vacancia(request):
    lotes_en_proceso = LoteReporteVacancia.objects.filter(
        usuario_generador=request.user,
        estado='EN_PROCESO'
    ).order_by('-fecha_creacion')

    if lotes_en_proceso.exists():
        lote = lotes_en_proceso.first()
        if lotes_en_proceso.count() > 1:
            for old_lote in lotes_en_proceso[1:]:
                old_lote.estado = 'CANCELADO'
                old_lote.save()
    else:
        lote = LoteReporteVacancia.objects.create(
            usuario_generador=request.user,
            estado='EN_PROCESO'
        )

    if request.method == 'POST':
        form = VacanciaForm(request.POST)
        if form.is_valid():
            maestro = form.cleaned_data['maestro_titular']
            escuela = maestro.id_escuela

            vacancia = form.save(commit=False)
            vacancia.lote = lote

            maestro_interino_obj = form.cleaned_data.get('maestro_interino')
            if maestro_interino_obj:
                vacancia.nombre_interino = f'{maestro_interino_obj.nombres} {maestro_interino_obj.a_paterno} {maestro_interino_obj.a_materno}'
                vacancia.curp_interino = maestro_interino_obj.curp
                if maestro_interino_obj.curp:
                    prelacion = Prelacion.objects.filter(curp=maestro_interino_obj.curp).first()
                    if prelacion:
                        vacancia.posicion_orden = prelacion.pos_orden
                        vacancia.folio_prelacion = prelacion.folio

            vacancia.direccion = f"{escuela.nombre_ct}, {escuela.domicilio}, DURANGO, {escuela.region}, {escuela.get_turno_display()}, ZONA ECONOMICA:{escuela.zona_economica}"
            
            apreciacion_desc = form.cleaned_data['apreciacion'].descripcion
            if apreciacion_desc.startswith("ADMISIÓN"):
                vacancia.destino = "Admisión"
            elif apreciacion_desc.startswith("PROMOCIÓN"):
                vacancia.destino = "Promoción vertical"
            else:
                vacancia.destino = ""

            vacancia.sostenimiento = "Federalizado" if escuela.sostenimiento == 'FEDERAL' else "Estatal"
            vacancia.turno = escuela.get_turno_display()
            vacancia.tipo_movimiento_reporte = form.cleaned_data['tipo_movimiento_original']
            
            hrs = maestro.hrs or "00.0"
            vacancia.tipo_plaza = "JORNADA" if hrs == "00.0" else "HORA/SEMANA/MES"
            if hrs == "00.0":
                vacancia.horas = None
            else:
                try:
                    vacancia.horas = str(int(float(hrs)))
                except (ValueError, TypeError):
                    vacancia.horas = None

            vacancia.municipio = escuela.region
            vacancia.zona_economica = f"Zona {escuela.zona_economica}"
            vacancia.categoria = maestro.categog.id_categoria if maestro.categog else ''
            vacancia.clave_presupuestal = maestro.clave_presupuestal
            vacancia.techo_financiero = maestro.techo_f
            vacancia.clave_ct = escuela.id_escuela
            vacancia.nombre_titular_reporte = f'{maestro.nombres} {maestro.a_paterno} {maestro.a_materno}'

            vacancia.save()

            Historial.objects.create(
                usuario=request.user,
                tipo_documento="Asignación de Vacancia",
                maestro=vacancia.maestro_titular,
                maestro_secundario_nombre=get_full_name(vacancia.maestro_interino) if vacancia.maestro_interino else '',
                ruta_archivo="",
                motivo="Asignación de Vacancia",
                lote_reporte=lote,
                datos_tramite={}
            )

            messages.success(request, "Vacancia agregada al lote actual.")
            return redirect('gestionar_lote_vacancia')
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = VacanciaForm()

    vacancias_en_lote = Vacancia.objects.filter(lote=lote).order_by('-id')
    context = {
        'form': form,
        'lote': lote,
        'vacancias_en_lote': vacancias_en_lote,
        'titulo': 'Generar Reporte de Vacancia'
    }
    return render(request, 'gestion_escolar/gestionar_lote_vacancia.html', context)

def _get_lote_y_vacancias(request, lote_id):
    lote = get_object_or_404(LoteReporteVacancia, id=lote_id, usuario_generador=request.user)
    vacancias = lote.vacancias.all()

    if not vacancias.exists():
        raise ValueError("No hay vacancias en este lote para exportar.")

    if lote.estado == 'GENERADO':
        messages.warning(request, "Este lote ya fue procesado anteriormente.")
        raise ValueError('Este lote ya fue procesado.')

    lote.estado = 'PROCESANDO'
    lote.save()
    return lote, vacancias

@login_required
@transaction.atomic
def exportar_paso_word(request, lote_id):
    try:
        lote, vacancias = _get_lote_y_vacancias(request, lote_id)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    plantilla_solicitud_asignacion = PlantillaTramite.objects.filter(nombre="SOLICITUD DE ASIGNACION").first()
    documentos_word_generados = 0
    word_docs_info = []

    if not plantilla_solicitud_asignacion:
        return JsonResponse({'status': 'warning', 'message': 'Plantilla "SOLICITUD DE ASIGNACION" no encontrada. Saltando paso de Word.', 'word_count': 0, 'word_docs': []})

    for vacancia in vacancias:
        if vacancia.maestro_interino and vacancia.fecha_inicio and vacancia.fecha_final:
            duration_months = get_month_diff(vacancia.fecha_inicio, vacancia.fecha_final)
            if duration_months <= 3:
                form_data_for_word = {
                    'plantilla': plantilla_solicitud_asignacion,
                    'maestro_titular': vacancia.maestro_titular,
                    'maestro_interino': vacancia.maestro_interino,
                    'fecha_efecto1': vacancia.fecha_inicio, 
                    'fecha_efecto2': vacancia.fecha_final,
                    'fecha_efecto3': vacancia.fecha_inicio, 
                    'fecha_efecto4': vacancia.fecha_final,
                    'folio': vacancia.folio_prelacion, 
                    'observaciones': vacancia.observaciones,
                    'no_prel_display': vacancia.posicion_orden, 
                    'folio_prel_display': vacancia.folio_prelacion,
                }
                
                motivo_tramite_obj = MotivoTramite.objects.filter(motivo_tramite=vacancia.tipo_movimiento_original).first()
                form_data_for_word['motivo_tramite'] = motivo_tramite_obj
                
                tipo_val_display = ''
                if vacancia.maestro_interino.curp:
                    prelacion = Prelacion.objects.filter(curp=vacancia.maestro_interino.curp).first()
                    if prelacion:
                        tipo_val_display = prelacion.tipo_val
                form_data_for_word['tipo_val_display'] = tipo_val_display

                success, doc_path = generate_word_document(form_data_for_word, plantilla_solicitud_asignacion, request.user)
                if success:
                    try:
                        historial_word = Historial.objects.create(
                            usuario=request.user,
                            tipo_documento=f"Oficio - {plantilla_solicitud_asignacion.nombre}",
                            maestro=vacancia.maestro_titular,
                            ruta_archivo=doc_path,
                            motivo=motivo_tramite_obj.motivo_tramite if motivo_tramite_obj else '',
                            maestro_secundario_nombre=get_full_name(vacancia.maestro_interino),
                            datos_tramite=serialize_form_data(form_data_for_word)
                        )
                        word_docs_info.append({
                            'id': historial_word.id,
                            'nombre': os.path.basename(doc_path),
                            'url': reverse('descargar_archivo_historial', args=[historial_word.id])
                        })
                        documentos_word_generados += 1
                    except Exception as e:
                        print(f"DEBUG: ❌ Error creando historial para Word: {e}")
    
    return JsonResponse({
        'status': 'success',
        'message': f'Se generaron {documentos_word_generados} documento(s) Word.',
        'word_count': documentos_word_generados,
        'word_docs': word_docs_info
    })

@login_required
@transaction.atomic
def exportar_paso_gsheets(request, lote_id):
    try:
        lote, vacancias = _get_lote_y_vacancias(request, lote_id)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    vacancias_enviadas = 0
    errores_gsheets = []
    for vacancia in vacancias:
        if vacancia.maestro_interino and vacancia.fecha_inicio and vacancia.fecha_final:
            google_sheet_row_data = [
                str(vacancias.filter(id__lte=vacancia.id).count()),
                datetime.now().strftime("%Y-%m-%d"),
                "EDUCACIÓN ESPECIAL",
                "Durango",
                vacancia.municipio or '',
                vacancia.direccion or '',
                vacancia.region or '',
                vacancia.zona_economica or '',
                vacancia.destino or '',
                vacancia.apreciacion.descripcion if vacancia.apreciacion else '',
                vacancia.get_tipo_vacante_display() or '',
                vacancia.tipo_plaza or '',
                vacancia.horas if vacancia.tipo_plaza == "HORA/SEMANA/MES" else '',
                vacancia.sostenimiento or '',
                vacancia.fecha_inicio.strftime("%Y-%m-%d") if vacancia.fecha_inicio else '',
                vacancia.fecha_final.strftime("%Y-%m-%d") if vacancia.fecha_final else '',
                vacancia.categoria or '',
                vacancia.pseudoplaza or '',
                vacancia.clave_presupuestal or '',
                vacancia.techo_financiero or '',
                vacancia.clave_ct or '',
                vacancia.turno or '',
                vacancia.tipo_movimiento_original or '',
                vacancia.observaciones or '',
                vacancia.maestro_interino.curp or '',
                '',
                vacancia.maestro_interino.form_academica or '',
                "N/A" if vacancia.tipo_plaza == "JORNADA" else (vacancia.apreciacion.descripcion if vacancia.apreciacion else ''),
                '', '', '', '',
                format_date_for_solicitud_asignacion(vacancia.fecha_inicio) if vacancia.fecha_inicio else '',
                format_date_for_solicitud_asignacion(vacancia.fecha_final) if vacancia.fecha_final else '',
                '', '',
                f"DEE/{vacancia.folio_prelacion}/2025" if vacancia.folio_prelacion else '',
                '', '',
            ]
            success_gs, message_gs = send_to_google_sheet(google_sheet_row_data)
            if not success_gs:
                error_msg = f"Fallo al enviar datos del interino '{get_full_name(vacancia.maestro_interino)}': {message_gs}"
                errores_gsheets.append(error_msg)
            else:
                vacancias_enviadas += 1
    
    mensaje_final = f'Se enviaron datos de {vacancias_enviadas} vacancia(s) a Google Sheets.'
    if errores_gsheets:
        mensaje_final += f' Hubo {len(errores_gsheets)} error(es).'

    return JsonResponse({
        'status': 'success',
        'message': mensaje_final,
        'gsheets_count': vacancias_enviadas,
        'gsheets_errors': errores_gsheets
    })

@login_required
@transaction.atomic
def exportar_paso_excel(request, lote_id):
    try:
        lote, vacancias = _get_lote_y_vacancias(request, lote_id)
        
        template_path = os.path.join(settings.BASE_DIR, 'tramites', 'Plantillas', 'Excel', 'FORMATOVACANCIAUSICAMM.xlsx')
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"No se encontró el template en la ruta: {template_path}")

        workbook = openpyxl.load_workbook(template_path)
        sheet = workbook.active
        
        row_num = 2
        campos_excel = [
            'nivel', 'entidad', 'municipio', 'direccion', 'region', 'zona_economica', 'destino', 'apreciacion',
            'tipo_vacante', 'tipo_plaza', 'horas', 'sostenimiento', 'fecha_inicio', 'fecha_final', 'categoria',
            'pseudoplaza', 'clave_presupuestal', 'techo_financiero', 'clave_ct', 'turno', 'tipo_movimiento_reporte', 'observaciones',
            'posicion_orden', 'folio_prelacion', 'curp_interino', 'nombre_interino'
        ]
        
        for vacancia in vacancias:
            for i, field_name in enumerate(campos_excel):
                cell = sheet.cell(row=row_num, column=i + 1)
                valor = ''
                
                try:
                    if field_name == 'curp_interino': 
                        valor = vacancia.maestro_interino.curp if vacancia.maestro_interino else vacancia.curp_interino or ''
                    elif field_name == 'nombre_interino': 
                        valor = get_full_name(vacancia.maestro_interino) if vacancia.maestro_interino else vacancia.nombre_interino or ''
                    elif field_name == 'apreciacion': 
                        valor = vacancia.apreciacion.descripcion if vacancia.apreciacion else ''
                    elif field_name == 'tipo_vacante': 
                        valor = vacancia.get_tipo_vacante_display().capitalize() if vacancia.tipo_vacante else ''
                    elif field_name == 'zona_economica':
                        valor = getattr(vacancia, field_name, '') or ''
                        if valor == 'Zona II':
                            valor = 'Zona 2'
                        elif valor == 'Zona III':
                            valor = 'Zona 3'
                    else: 
                        valor = getattr(vacancia, field_name, '') or ''
                        
                    if field_name in ['fecha_inicio', 'fecha_final'] and valor and isinstance(valor, (datetime, date)):
                        valor = valor.strftime("%Y-%m-%d")
                            
                except Exception as field_error:
                    valor = f"Error: {field_error}"
                
                cell.value = valor
                
            row_num += 1

        output_dir = os.path.join(settings.MEDIA_ROOT, 'reportes_vacancias')
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"VACANCIA_{timestamp}.xlsx"
        output_path_server = os.path.join(output_dir, output_filename)
        
        workbook.save(output_path_server)

        historial_excel = Historial.objects.create(
            usuario=request.user, 
            tipo_documento="Reporte de Vacancia", 
            maestro=None,
            ruta_archivo=output_path_server, 
            motivo="Reporte de Vacancia", 
            lote_reporte=lote
        )
        
        lote.archivo_generado = os.path.join('reportes_vacancias', output_filename)
        lote.estado = 'GENERADO'
        lote.fecha_generado = datetime.now()
        lote.save()

        response_data = {
            'status': 'success',
            'message': f'Lote procesado exitosamente.',
            'excel_url': reverse('descargar_archivo_historial', args=[historial_excel.id]),
            'excel_name': output_filename
        }

        return JsonResponse(response_data)

    except Exception as e:
        import traceback
        print(f"DEBUG: ❌ Error generando Excel: {str(e)}")
        print(f"DEBUG: Traceback completo: {traceback.format_exc()}")
        
        messages.error(request, f"Error al generar el archivo Excel: {str(e)}")
        lote.estado = 'EN_PROCESO'
        lote.save()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def eliminar_vacancia_lote(request, pk):
    if request.method == 'POST':
        vacancia = get_object_or_404(Vacancia, pk=pk)
        if vacancia.lote.usuario_generador == request.user and vacancia.lote.estado == 'EN_PROCESO':
            vacancia.delete()
            messages.success(request, "Vacancia eliminada del lote correctamente.")
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': 'No autorizado para eliminar esta vacancia.'}, status=403)
    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)
