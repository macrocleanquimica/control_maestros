import json
import re
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdf_canvas

from ..models import Escuela, Zona

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

PALETA = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
    "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000",
    "#aaffc3", "#808000", "#ffd8b1", "#000075", "#808080",
]

HEX_RE = re.compile(r'^#([0-9a-fA-F]{6})$')


@lru_cache(maxsize=None)
def _cargar_json(nombre):
    ruta = DATA_DIR / nombre
    if not ruta.exists():
        return None
    with open(ruta, encoding='utf-8') as fh:
        return json.load(fh)


def _geojson_municipios():
    return _cargar_json('municipios_durango.geojson')


def _centroides():
    data = _cargar_json('municipios_durango_centroides.json')
    return {c['municipio']: c for c in data or []}


def _normalizacion():
    return _cargar_json('normalizacion_municipios.json') or {}


def _normalizar_municipio(valor):
    if not valor:
        return None
    valor = str(valor).strip()
    if valor in _centroides():
        return valor
    return _normalizacion().get(valor)


def _centroides_lista():
    return [{'municipio': c['municipio'], 'lng': c['lng'], 'lat': c['lat']}
            for c in _cargar_json('municipios_durango_centroides.json') or []]


def _colores_por_zona():
    zonas = list(Zona.objects.order_by('numero'))
    return {z.numero: PALETA[i % len(PALETA)] for i, z in enumerate(zonas)}


def _puntos_ct():
    colores = _colores_por_zona()
    centroides = _centroides()
    escuelas = Escuela.objects.select_related('zona_esc').order_by('zona_esc__numero', 'nombre_ct')
    puntos = []
    sin_ubicacion = []
    for esc in escuelas:
        zona_num = esc.zona_esc.numero if esc.zona_esc else None
        municipio = _normalizar_municipio(esc.region)
        centro = centroides.get(municipio) if municipio else None
        punto = {
            'cct': esc.id_escuela,
            'nombre': esc.nombre_ct,
            'zona': zona_num,
            'zona_etiqueta': esc.zona_esc.etiqueta if esc.zona_esc else 'Sin zona',
            'color': colores.get(zona_num, '#808080'),
            'municipio': municipio or (esc.region or 'Sin municipio'),
            'url': reverse('detalle_escuela', args=[esc.id]),
        }
        if centro:
            punto['lng'] = centro['lng']
            punto['lat'] = centro['lat']
            puntos.append(punto)
        else:
            punto['region_original'] = esc.region
            sin_ubicacion.append(punto)
    return puntos, sin_ubicacion


def _datos_zonas(puntos):
    colores = _colores_por_zona()
    return [
        {
            'numero': zona.numero,
            'etiqueta': zona.etiqueta,
            'color': colores.get(zona.numero, '#808080'),
            'cantidad': sum(1 for p in puntos if p['zona'] == zona.numero),
        }
        for zona in Zona.objects.order_by('numero')
    ]


def _resumen_municipios(puntos):
    conteos = {}
    for p in puntos:
        clave = p['municipio']
        conteos[clave] = conteos.get(clave, 0) + 1
    return [{'nombre': k, 'cantidad': v} for k, v in sorted(conteos.items())]


@login_required
@permission_required('gestion_escolar.view_escuela', raise_exception=True)
def mapa_zonas(request):
    if request.user.groups.filter(name='Directores').exists():
        raise PermissionDenied

    puntos, sin_ubicacion = _puntos_ct()

    context = {
        'titulo': 'Mapa de Zonas',
        'geojson': json.dumps(_geojson_municipios(), ensure_ascii=False),
        'centroides': json.dumps(_centroides_lista(), ensure_ascii=False),
        'puntos': json.dumps(puntos, ensure_ascii=False),
        'zonas': _datos_zonas(puntos),
        'municipios': _resumen_municipios(puntos),
        'sin_ubicacion': sin_ubicacion,
        'total_ct': len(puntos),
        'total_sin_ubicacion': len(sin_ubicacion),
    }
    return render(request, 'gestion_escolar/mapa_zonas.html', context)


@login_required
@permission_required('gestion_escolar.view_escuela', raise_exception=True)
def mapa_zonas_pdf(request):
    if request.user.groups.filter(name='Directores').exists():
        raise PermissionDenied

    puntos, sin_ubicacion = _puntos_ct()
    colores = _colores_por_zona()
    zonas = list(Zona.objects.order_by('numero'))
    color_municipio = _color_por_municipio(puntos, colores)

    contenido = _generar_pdf(puntos, colores, zonas, color_municipio, _datos_anexo())

    response = HttpResponse(contenido, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="mapa_zonas_durango.pdf"'
    return response


def _limites_geo(geojson):
    lngs = []
    lats = []

    def barrido(ring):
        for lng, lat in ring:
            lngs.append(lng)
            lats.append(lat)

    for feat in geojson['features']:
        geom = feat['geometry']
        polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
        for poly in polys:
            if not poly:
                continue
            barrido(poly[0])
            for hole in poly[1:]:
                barrido(hole)
    return min(lngs), max(lngs), min(lats), max(lats)


def _color_por_municipio(puntos, colores):
    conteo = {}
    for p in puntos:
        conteo.setdefault(p['municipio'], {})
        zona = p['zona']
        if zona is not None:
            conteo[p['municipio']][zona] = conteo[p['municipio']].get(zona, 0) + 1
    return {
        m: colores.get(max(zc, key=zc.get), '#d9dee5')
        for m, zc in conteo.items()
    }


def _rgb(hex_color):
    match = HEX_RE.match(hex_color or '#808080')
    if not match:
        return (0.5, 0.5, 0.5)
    return tuple(int(match.group(1)[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _es_color_clara(hex_color):
    r, g, b = _rgb(hex_color)
    return 0.299 * r + 0.587 * g + 0.114 * b > 0.55


def _mezclar_blanco(hex_color, proporcion):
    r, g, b = _rgb(hex_color)
    p = proporcion
    return (p * r + (1 - p), p * g + (1 - p), p * b + (1 - p))


def _datos_anexo():
    colores = _colores_por_zona()
    escuelas = Escuela.objects.select_related('zona_esc').order_by('zona_esc__numero', 'nombre_ct')
    de_zonas = {}
    for esc in escuelas:
        zona = esc.zona_esc.numero if esc.zona_esc else None
        etiqueta = esc.zona_esc.etiqueta if esc.zona_esc else None
        domicilio = (esc.domicilio or '').strip()
        region = (esc.region or '').strip()
        direccion = ', '.join(p for p in (domicilio, region) if p) or 'S/D'
        de_zonas.setdefault(zona, []).append((etiqueta, esc.id_escuela, esc.nombre_ct, direccion))
    resultado = []
    for zona in sorted(k for k in de_zonas if k is not None):
        resultado.append({
            'numero': zona,
            'etiqueta': de_zonas[zona][0][0],
            'color': colores.get(zona, '#808080'),
            'filas': [(cct, nombre, direccion) for _, cct, nombre, direccion in de_zonas[zona]],
        })
    if None in de_zonas:
        resultado.append({
            'numero': None,
            'etiqueta': 'SIN ZONA',
            'color': '#808080',
            'filas': [(cct, nombre, direccion) for _, cct, nombre, direccion in de_zonas[None]],
        })
    return resultado


def _ajustar(cv, texto, fuente, tamano, max_ancho):
    if cv.stringWidth(texto, fuente, tamano) <= max_ancho:
        return texto
    recortado = texto
    while recortado and cv.stringWidth(recortado + '...', fuente, tamano) > max_ancho:
        recortado = recortado[:-1]
    return recortado + '...'


def _dibujar_anexo(cv, datos, page_w, page_h):
    margen = 40.0
    ancho = page_w - 2 * margen
    ancho_cct = 75.0
    ancho_nombre = 235.0
    ancho_dir = ancho - ancho_cct - ancho_nombre
    alto_zona = 24.0
    alto_color = 16.0
    alto_fila = 16.0
    holgura = 5.0
    margen_bajo = 50.0
    top = page_h - 100.0

    fuente = 'Helvetica'
    fuente_b = 'Helvetica-Bold'

    def cabecera_pagina():
        cv.setFillColorRGB(0.1, 0.1, 0.2)
        cv.setFont(fuente_b, 12)
        cv.drawString(margen, page_h - 60, 'Anexo - Directorio de Centros de Trabajo por Zona')
        cv.setFont(fuente, 8.5)
        cv.setFillColorRGB(0.4, 0.4, 0.4)
        cv.drawString(margen, page_h - 74,
                      'Clave, nombre y dirección de cada centro de trabajo, agrupado por zona escolar.')
        cv.setLineWidth(0.6)
        cv.setStrokeColorRGB(0.65, 0.68, 0.75)
        cv.line(margen, page_h - 80, page_w - margen, page_h - 80)

    def banda_zona(zone, y0):
        cv.setFillColorRGB(*_rgb(zone['color']))
        cv.rect(margen, y0 - alto_zona, ancho, alto_zona, stroke=0, fill=1)
        if _es_color_clara(zone['color']):
            cv.setFillColorRGB(0.15, 0.15, 0.2)
        else:
            cv.setFillColorRGB(1, 1, 1)
        cv.setFont(fuente_b, 10)
        cv.drawString(margen + 8, y0 - alto_zona + 7, '%s   (%d C.T.)' % (zone['etiqueta'], len(zone['filas'])))

    def encabezado_columnas(ctop):
        cv.setFillColorRGB(0.93, 0.94, 0.96)
        cv.rect(margen, ctop - alto_color, ancho, alto_color, stroke=0, fill=1)
        cv.setFillColorRGB(0.35, 0.4, 0.48)
        cv.setFont(fuente_b, 8)
        bas = ctop - alto_color + 5
        cv.drawString(margen + 8, bas, 'C.C.T.')
        cv.drawString(margen + 8 + ancho_cct, bas, 'NOMBRE')
        cv.drawString(margen + 8 + ancho_cct + ancho_nombre, bas, 'DIRECCIÓN')

    cabecera_pagina()
    y = top

    for zone in datos:
        alto_bloque = alto_zona + alto_color + alto_fila * len(zone['filas']) + holgura + 14.0
        if y - alto_bloque < margen_bajo:
            cv.showPage()
            y = top
            cabecera_pagina()

        y -= 14.0  # separación entre bloques de zona
        banda_zona(zone, y)
        ctop = y - alto_zona
        encabezado_columnas(ctop)
        rt = ctop - alto_color - holgura
        for i, (cct, nombre, direccion) in enumerate(zone['filas']):
            if rt - alto_fila < margen_bajo:
                cv.showPage()
                y = top
                cabecera_pagina()
                banda_zona(zone, y)
                ctop = y - alto_zona
                encabezado_columnas(ctop)
                rt = ctop - alto_color - holgura
            if i % 2 == 1:
                cv.setFillColorRGB(0.96, 0.97, 0.98)
                cv.rect(margen, rt - alto_fila, ancho, alto_fila, stroke=0, fill=1)
            cv.setFont(fuente, 8)
            cv.setFillColorRGB(0.15, 0.2, 0.28)
            bas = rt - 5
            cv.drawString(margen + 8, bas, _ajustar(cv, cct, fuente, 8, ancho_cct + 14))
            cv.drawString(margen + 8 + ancho_cct, bas, _ajustar(cv, nombre, fuente, 8, ancho_nombre))
            cv.drawString(margen + 8 + ancho_cct + ancho_nombre, bas,
                          _ajustar(cv, direccion, fuente, 8, ancho_dir - 12))
            rt -= alto_fila
        y = rt


def _generar_pdf(puntos, colores, zonas, color_municipio, datos_anexo):
    geojson = _geojson_municipios()
    centroides = _centroides()
    min_lng, max_lng, min_lat, max_lat = _limites_geo(geojson)

    page_w, page_h = A4
    margen_lateral = 1.6 * cm
    margen_sup = 1.9 * cm
    margen_inf = 4.2 * cm  # deja espacio para leyenda y resumen

    ancho_dispo = page_w - 2 * margen_lateral
    alto_dispo = page_h - margen_sup - margen_inf

    ancho_geo = max_lng - min_lng
    alto_geo = max_lat - min_lat
    escala = min(ancho_dispo / ancho_geo, alto_dispo / alto_geo)

    # Centra el mapa en el área disponible
    ancho_mapa = ancho_geo * escala
    alto_mapa = alto_geo * escala
    offset_x = margen_lateral + (ancho_dispo - ancho_mapa) / 2.0
    offset_y = margen_inf + (alto_dispo - alto_mapa) / 2.0

    def to_x(lng):
        return offset_x + (lng - min_lng) * escala

    def to_y(lat):
        return offset_y + (lat - min_lat) * escala

    buffer = BytesIO()
    cv = pdf_canvas.Canvas(buffer, pagesize=A4)
    cv.setTitle('Mapa de Zonas - Centros de Trabajo de Durango')

    # Fondo del mapa
    cv.setFillColorRGB(0.97, 0.97, 0.97)
    cv.rect(offset_x, offset_y, ancho_mapa, alto_mapa, stroke=0, fill=1)

    # Polígonos de municipios (relleno con tinte de la zona dominante)
    cv.setStrokeColorRGB(0.62, 0.66, 0.72)
    cv.setLineWidth(0.5)
    for feat in geojson['features']:
        nombre = feat['properties'].get('nom_agem')
        hex_fill = color_municipio.get(nombre, '#e5e7eb')
        cv.setFillColorRGB(*_mezclar_blanco(hex_fill, 0.35))
        geom = feat['geometry']
        polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
        for poly in polys:
            if not poly:
                continue
            path = cv.beginPath()
            path.moveTo(to_x(poly[0][0][0]), to_y(poly[0][0][1]))
            for lng, lat in poly[0][1:]:
                path.lineTo(to_x(lng), to_y(lat))
            path.close()
            cv.drawPath(path, stroke=1, fill=1)

    # Nombre de cada municipio en su centroide
    cv.setFont('Helvetica-Bold', 6.5)
    for nombre, c in centroides.items():
        cv.setFillColorRGB(0.25, 0.28, 0.33)
        cv.drawCentredString(to_x(c['lng']), to_y(c['lat']) - 2, nombre)

    # Puntos de C.T. coloreados por zona
    for p in puntos:
        match = HEX_RE.match(p['color'])
        if not match:
            continue
        r, g, b = (int(match.group(1)[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        cv.setFillColorRGB(r, g, b)
        cv.setStrokeColorRGB(1, 1, 1)
        cv.setLineWidth(0.8)
        cv.circle(to_x(p['lng']), to_y(p['lat']), 3.2, stroke=1, fill=1)

    # Título
    cv.setFillColorRGB(0.1, 0.1, 0.2)
    cv.setFont('Helvetica-Bold', 14)
    cv.drawString(margen_lateral, page_h - 1.3 * cm,
                  'Mapa de Zonas - Centros de Trabajo de Durango')
    cv.setFont('Helvetica', 9)
    cv.setFillColorRGB(0.4, 0.4, 0.4)
    cv.drawString(margen_lateral, page_h - 1.75 * cm,
                  'C.T. ubicados en el centroide de su municipio (INEGI 2025)')

    # Leyenda de zonas en columnas abajo
    cv.setFont('Helvetica', 8)
    ancho_leyenda = ancho_dispo
    col_ancho = ancho_leyenda / 3.0
    y_l = margen_inf - 0.7 * cm
    for i, zona in enumerate(zonas):
        col = i % 3
        fila = i // 3
        x_l = margen_lateral + col * col_ancho
        y_r = y_l - fila * 0.5 * cm
        hex_color = colores.get(zona.numero, '#808080')
        cv.setFillColorRGB(*_rgb(hex_color))
        cv.rect(x_l + 1, y_r, 0.28 * cm, 0.28 * cm, stroke=0, fill=1)
        cv.setFillColorRGB(0.1, 0.1, 0.2)
        cv.drawString(x_l + 0.42 * cm, y_r + 2,
                      _ajustar(cv, zona.etiqueta, 'Helvetica', 8, col_ancho - 0.5 * cm))

    # Resumen
    cv.setFont('Helvetica', 9)
    cv.setFillColorRGB(0.3, 0.3, 0.3)
    cv.drawString(margen_lateral, 1.0 * cm, 'Total de C.T.: %d' % len(puntos))
    if puntos:
        cv.drawString(margen_lateral + 3.2 * cm, 1.0 * cm,
                      'Municipios con C.T.: %d' % len({p['municipio'] for p in puntos}))

    cv.showPage()

    _dibujar_anexo(cv, datos_anexo, page_w, page_h)
    cv.save()
    return buffer.getvalue()