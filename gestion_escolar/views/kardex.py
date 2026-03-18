from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Q
from django.utils import timezone
from datetime import datetime

from ..models import Maestro, Historial, RegistroCorrespondencia, KardexMovimiento, FUP, DocumentoExpediente

@login_required
def kardex_maestros_ajax(request):
    draw = int(request.GET.get('draw', 0))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    order_column_index = int(request.GET.get('order[0][column]', 0))
    order_dir = request.GET.get('order[0][dir]', 'asc')
    column_names = ['a_paterno', 'clave_presupuestal'] 
    order_column = column_names[order_column_index]
    if order_dir == 'desc':
        order_column = f'-{order_column}'

    queryset = Maestro.objects.all().exclude(id_maestro__isnull=True).exclude(id_maestro='')
    records_total = queryset.count()

    if search_value:
        from unidecode import unidecode
        search_value_upper = search_value.upper()
        search_terms = search_value_upper.split()
        table_name = Maestro._meta.db_table
        
        where_clauses = []
        params = []

        for term in search_terms:
            unaccented_term = f'%{unidecode(term)}%'
            term_with_wildcards = f'%{term}%'
            
            term_clause = f"""(
                UPPER(unaccent({table_name}.nombres)) LIKE %s OR
                UPPER(unaccent({table_name}.a_paterno)) LIKE %s OR
                UPPER(unaccent({table_name}.a_materno)) LIKE %s OR
                UPPER({table_name}.clave_presupuestal) LIKE %s
            )"""
            where_clauses.append(term_clause)
            
            params.extend([unaccented_term, unaccented_term, unaccented_term, term_with_wildcards])

        if where_clauses:
            queryset = queryset.extra(where=[" AND ".join(where_clauses)], params=params)

    records_filtered = queryset.count()
    queryset = queryset.order_by(order_column)[start:start + length]

    data = []
    for maestro in queryset:
        kardex_url = reverse("kardex_maestro_detail", args=[maestro.pk]) + "?from=lista"
        actions = f'<a href="{kardex_url}" class="btn btn-sm btn-warning">Ver Kardex</a>'
        data.append([
            f'{maestro.a_paterno} {maestro.a_materno} {maestro.nombres}',
            maestro.clave_presupuestal or '-',
            actions
        ])

    response = {
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
    }
    return JsonResponse(response)

@permission_required('gestion_escolar.acceder_kardex', raise_exception=True)
def kardex_maestro_list(request):
    context = {
        'titulo': 'Kardex del Personal'
    }
    return render(request, 'gestion_escolar/kardex_list.html', context)

@permission_required('gestion_escolar.acceder_kardex', raise_exception=True)
def kardex_maestro_detail(request, maestro_id):
    maestro = get_object_or_404(Maestro, pk=maestro_id)
    
    from_page = request.GET.get('from', 'lista')
    
    timeline = []

    maestro_full_name = f"{maestro.nombres or ''} {maestro.a_paterno or ''} {maestro.a_materno or ''}".strip()
    historial_maestro = Historial.objects.filter(
        Q(maestro=maestro) | Q(maestro_secundario_nombre=maestro_full_name)
    ).select_related('usuario')
    # Pre-cargar vacancias para el historial
    from ..models import Vacancia
    vacancias_list = {v.maestro_titular_id: v for v in Vacancia.objects.filter(maestro_titular=maestro)}

    for item in historial_maestro:
        detalle_display = item.motivo or 'Ver documento'
        # Si es una asignación de vacancia, buscar detalles adicionales
        if item.tipo_documento == "Asignación de Vacancia":
            if item.datos_tramite:
                try:
                    inicio = item.datos_tramite.get('fecha_inicio', 'N/A')
                    fin = item.datos_tramite.get('fecha_final', 'Indefinido')
                    interino = item.datos_tramite.get('interino', 'N/A')
                    detalle_display = f"Periodo: {inicio} al {fin} | Interino: {interino}"
                except:
                    pass
            elif maestro.pk in vacancias_list:
                # Fallback para registros antiguos sin datos_tramite poblados
                v = vacancias_list[maestro.pk]
                detalle_display = f"Periodo: {v.fecha_inicio} al {v.fecha_final or 'Indefinido'} | Interino: {v.nombre_interino or 'N/A'}"

        timeline.append({
            'fecha': item.fecha_creacion,
            'tipo': 'Trámite',
            'descripcion': item.tipo_documento,
            'detalle': detalle_display,
            'usuario': item.usuario.username if item.usuario else 'Sistema',
            'objeto': item
        })

    correspondencia_recibida = RegistroCorrespondencia.objects.filter(maestro=maestro)
    for item in correspondencia_recibida:
        fecha_dt_naive = datetime.combine(item.fecha_recibido, datetime.min.time())
        fecha_dt_aware = timezone.make_aware(fecha_dt_naive, timezone.get_current_timezone())
        timeline.append({
            'fecha': fecha_dt_aware,
            'tipo': 'Correspondencia',
            'descripcion': f"Recibido: {item.get_tipo_documento_display()} de {item.remitente}",
            'detalle': item.contenido,
            'usuario': item.quien_recibio or 'N/A',
            'objeto': item
        })

    movimientos_kardex = KardexMovimiento.objects.filter(maestro=maestro).select_related('usuario')
    for item in movimientos_kardex:
        timeline.append({
            'fecha': item.fecha,
            'tipo': 'Movimiento Manual',
            'descripcion': 'Anotación en Kardex',
            'detalle': item.descripcion,
            'usuario': item.usuario.username if item.usuario else 'Sistema',
            'objeto': item
        })

    fups_maestro = FUP.objects.filter(maestro=maestro)
    for item in fups_maestro:
        fecha_dt_naive = datetime.combine(item.fecha, datetime.min.time())
        fecha_dt_aware = timezone.make_aware(fecha_dt_naive, timezone.get_current_timezone())
        
        detalle_partes = [f"Folio: {item.folio}"]
        if item.efectos:
            detalle_partes.append(f"Efectos: {item.efectos}")
        if item.techo_financiero:
            detalle_partes.append(f"Techo: {item.techo_financiero}")
        if item.observaciones:
            detalle_partes.append(f"Obs: {item.observaciones}")

        timeline.append({
            'fecha': fecha_dt_aware,
            'tipo': 'FUP',
            'descripcion': 'Captura de FUP',
            'detalle': " | ".join(detalle_partes),
            'usuario': 'Sistema',
            'objeto': item
        })

    documentos_expediente = DocumentoExpediente.objects.filter(maestro=maestro).select_related('subido_por')
    for item in documentos_expediente:
        timeline.append({
            'fecha': item.fecha_subida,
            'tipo': 'Expediente',
            'descripcion': f"Documento Anexado: {item.get_tipo_documento_display()}",
            'detalle': f"Archivo: {item.get_file_name()}",
            'usuario': item.subido_por.username if item.subido_por else 'N/A',
            'objeto': item
        })

    timeline.sort(key=lambda x: x['fecha'], reverse=True)

    context = {
        'maestro': maestro,
        'timeline': timeline,
        'titulo': f'Kardex de {maestro}',
        'from_page': from_page
    }
    
    return render(request, 'gestion_escolar/kardex_detail.html', context)
