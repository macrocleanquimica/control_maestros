from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Q
from django.utils import timezone
from datetime import datetime

from ..models import Maestro, Historial, RegistroCorrespondencia, KardexMovimiento, FUP, DocumentoExpediente, Vacancia, Interinato


def _ids_y_plazas_persona(maestro):
    """IDs de todos los registros (plazas/claves) de la misma persona.

    Combina el vínculo oficial (maestro_principal -> raíz + secundarias)
    con hermanas por CURP (misma persona sin vínculo). Así el Kardex muestra
    de una sola vez los movimientos de todas sus claves.
    """
    raiz = maestro
    vistos = set()
    while getattr(raiz, 'maestro_principal_id', None):
        if raiz.pk in vistos:
            break
        vistos.add(raiz.pk)
        padre = Maestro.objects.filter(pk=raiz.maestro_principal_id).first()
        if not padre:
            break
        raiz = padre
    ids = {raiz.pk}
    ids.update(
        Maestro.objects.filter(maestro_principal=raiz).values_list('pk', flat=True)
    )
    if maestro.curp and str(maestro.curp).strip():
        ids.update(
            Maestro.objects.filter(curp__iexact=str(maestro.curp).strip()).values_list('pk', flat=True)
        )
    plazas = list(Maestro.objects.filter(pk__in=ids).select_related('id_escuela').order_by('id_maestro'))
    nombres = {
        f"{m.nombres or ''} {m.a_paterno or ''} {m.a_materno or ''}".strip()
        for m in plazas
    }
    nombres.discard('')
    return list(ids), plazas, list(nombres)


def _raiz_de(pk, mapa_padre):
    """Sube por maestro_principal usando un mapa {pk: padre_pk} ya cargado."""
    actual = pk
    vistos = set()
    while mapa_padre.get(actual) and actual not in vistos:
        vistos.add(actual)
        actual = mapa_padre[actual]
    return actual

@login_required
@permission_required('gestion_escolar.acceder_kardex', raise_exception=True)
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

    queryset = Maestro.objects.filter(maestro_principal__isnull=True).exclude(id_maestro__isnull=True).exclude(id_maestro='')
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
            # Buscar en TODAS las plazas (no solo raíces): si una secundaria
            # coincide, se muestra la persona (su raíz).
            coincidentes = Maestro.objects.all().extra(where=[" AND ".join(where_clauses)], params=params)
            mapa_padre = dict(Maestro.objects.values_list('pk', 'maestro_principal_id'))
            raices = {_raiz_de(pk, mapa_padre) for pk in coincidentes.values_list('pk', flat=True)}
            queryset = queryset.filter(pk__in=raices)

    records_filtered = queryset.count()
    queryset = queryset.order_by(order_column).prefetch_related('plazas_secundarias')[start:start + length]

    data = []
    for raiz in queryset:
        secundarias = list(raiz.plazas_secundarias.all().order_by('id_maestro'))
        claves = [c for c in [raiz.clave_presupuestal] + [s.clave_presupuestal for s in secundarias] if c]
        if claves:
            claves_html = ' '.join(
                f'<span class="badge bg-light text-dark border font-monospace me-1">{c}</span>' for c in claves
            )
            if len(claves) > 1:
                claves_html += f' <span class="badge bg-warning text-dark ms-1">{len(claves)} plazas</span>'
        else:
            claves_html = '-'
        kardex_url = reverse("kardex_maestro_detail", args=[raiz.pk]) + "?from=lista"
        actions = f'<a href="{kardex_url}" class="comp-action comp-action-view" title="Ver kardex" aria-label="Ver kardex del maestro"><i class="fas fa-file-lines"></i></a>'
        data.append([
            f'{raiz.a_paterno} {raiz.a_materno} {raiz.nombres}',
            claves_html,
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

    # --- Kardex unificado: todas las plazas/claves de la misma persona ---
    ids_persona, plazas, nombres_persona = _ids_y_plazas_persona(maestro)

    timeline = []

    filtros_historial = Q(maestro_id__in=ids_persona) | Q(datos_tramite__maestro_interino__in=ids_persona)
    if nombres_persona:
        filtros_historial |= Q(maestro_secundario_nombre__in=nombres_persona)
    historial_maestro = Historial.objects.filter(filtros_historial).select_related('usuario', 'maestro')
    # Vacancias donde fue titular o interino (para el fallback de registros antiguos)
    vacancias_titular = {v.maestro_titular_id: v for v in Vacancia.objects.filter(maestro_titular_id__in=ids_persona)}
    vacancias_interino = {v.maestro_interino_id: v for v in Vacancia.objects.filter(maestro_interino_id__in=ids_persona) if v.maestro_interino_id}

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
                except Exception:
                    pass
            elif item.maestro_id in vacancias_titular:
                # Fallback para registros antiguos sin datos_tramite poblados
                v = vacancias_titular[item.maestro_id]
                detalle_display = f"Periodo: {v.fecha_inicio} al {v.fecha_final or 'Indefinido'} | Interino: {v.nombre_interino or 'N/A'}"

        datos = item.datos_tramite or {}
        clave_mov = ''
        if item.maestro_id and getattr(item.maestro, 'clave_presupuestal', None):
            clave_mov = item.maestro.clave_presupuestal
        if not clave_mov:
            clave_mov = str(datos.get('CLAVE_PRESUPUESTAL_TITULAR') or datos.get('clave_presupuestal_titular_display') or '')
        rol = 'Titular' if item.maestro_id in ids_persona else 'Interino'
        timeline.append({
            'fecha': item.fecha_creacion,
            'tipo': 'Trámite',
            'descripcion': item.tipo_documento,
            'detalle': detalle_display,
            'usuario': item.usuario.username if item.usuario else 'Sistema',
            'objeto': item,
            'clave': clave_mov,
            'rol': rol,
        })

    correspondencia_recibida = RegistroCorrespondencia.objects.filter(maestro_id__in=ids_persona).select_related('maestro')
    for item in correspondencia_recibida:
        fecha_dt_naive = datetime.combine(item.fecha_recibido, datetime.min.time())
        fecha_dt_aware = timezone.make_aware(fecha_dt_naive, timezone.get_current_timezone())
        timeline.append({
            'fecha': fecha_dt_aware,
            'tipo': 'Correspondencia',
            'descripcion': f"Recibido: {item.get_tipo_documento_display()} de {item.remitente}",
            'detalle': item.contenido,
            'usuario': item.quien_recibio or 'N/A',
            'objeto': item,
            'clave': item.maestro.clave_presupuestal if item.maestro_id and item.maestro else '',
            'rol': '',
        })

    movimientos_kardex = KardexMovimiento.objects.filter(maestro_id__in=ids_persona).select_related('usuario', 'maestro')
    for item in movimientos_kardex:
        timeline.append({
            'fecha': item.fecha,
            'tipo': 'Movimiento Manual',
            'descripcion': 'Anotación en Kardex',
            'detalle': item.descripcion,
            'usuario': item.usuario.username if item.usuario else 'Sistema',
            'objeto': item,
            'clave': item.maestro.clave_presupuestal if item.maestro_id and item.maestro else '',
            'rol': '',
        })

    fups_maestro = FUP.objects.filter(maestro_id__in=ids_persona).select_related('maestro')
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
            'objeto': item,
            'clave': item.clave_presupuestal or (item.maestro.clave_presupuestal if item.maestro_id and item.maestro else ''),
            'rol': '',
        })

    documentos_expediente = DocumentoExpediente.objects.filter(maestro_id__in=ids_persona).select_related('subido_por', 'maestro')
    for item in documentos_expediente:
        timeline.append({
            'fecha': item.fecha_subida,
            'tipo': 'Expediente',
            'descripcion': f"Documento Anexado: {item.get_tipo_documento_display()}",
            'detalle': f"Archivo: {item.get_file_name()}",
            'usuario': item.subido_por.username if item.subido_por else 'N/A',
            'objeto': item,
            'clave': item.maestro.clave_presupuestal if item.maestro_id and item.maestro else '',
            'rol': '',
        })

    # Interinatos: plazas que cubrió como interino y coberturas de sus plazas como titular
    inter_cubiertos = Interinato.objects.filter(
        maestro_interino_id__in=ids_persona
    ).select_related('maestro_titular', 'escuela')
    for inter in inter_cubiertos:
        titular = (
            f"{inter.maestro_titular.nombres or ''} {inter.maestro_titular.a_paterno or ''} {inter.maestro_titular.a_materno or ''}".strip()
            if inter.maestro_titular_id and inter.maestro_titular else '—'
        )
        fin = inter.fecha_final.strftime('%d/%m/%Y') if inter.fecha_final else 'vigente'
        timeline.append({
            'fecha': inter.fecha_registro,
            'tipo': 'Interinato',
            'descripcion': f"Cubrió plaza de {titular}",
            'detalle': f"CCT {inter.escuela.id_escuela if inter.escuela_id and inter.escuela else '—'} | {inter.fecha_inicio.strftime('%d/%m/%Y') if inter.fecha_inicio else '?'} al {fin} | {inter.motivo or 's/motivo'} | {inter.get_estatus_display()}",
            'usuario': 'Sistema',
            'objeto': inter,
            'clave': inter.clave_presupuestal or '',
            'rol': 'Interino',
        })

    inter_como_titular = Interinato.objects.filter(
        maestro_titular_id__in=ids_persona
    ).select_related('maestro_interino', 'escuela')
    for inter in inter_como_titular:
        interino = (
            f"{inter.maestro_interino.nombres or ''} {inter.maestro_interino.a_paterno or ''} {inter.maestro_interino.a_materno or ''}".strip()
            if inter.maestro_interino_id and inter.maestro_interino else '—'
        )
        fin = inter.fecha_final.strftime('%d/%m/%Y') if inter.fecha_final else 'vigente'
        timeline.append({
            'fecha': inter.fecha_registro,
            'tipo': 'Interinato',
            'descripcion': f"Su plaza cubierta por {interino}",
            'detalle': f"CCT {inter.escuela.id_escuela if inter.escuela_id and inter.escuela else '—'} | {inter.fecha_inicio.strftime('%d/%m/%Y') if inter.fecha_inicio else '?'} al {fin} | {inter.motivo or 's/motivo'} | {inter.get_estatus_display()}",
            'usuario': 'Sistema',
            'objeto': inter,
            'clave': inter.clave_presupuestal or '',
            'rol': 'Titular',
        })

    timeline.sort(key=lambda x: x['fecha'], reverse=True)

    context = {
        'maestro': maestro,
        'plazas': plazas,
        'total_plazas': len(plazas),
        'timeline': timeline,
        'titulo': f'Kardex de {maestro}',
        'from_page': from_page
    }

    return render(request, 'gestion_escolar/kardex_detail.html', context)
