"""Diseñador de plantillas de Word.

Permite a los administradores crear plantillas propias a partir de un .docx,
elegir qué datos pide el formulario, qué motivos acepta y qué campos
personalizados agrega. Las 23 plantillas que ya existían son del sistema y
solo se consultan: no se editan ni se eliminan.
"""

import itertools
import re
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from ..campos_plantilla import (
    CAMPOS_SOLO_LECTURA,
    CATALOGO_CAMPOS,
    TIPOS_CAMPO_PERSONALIZADO,
    campos_por_seccion,
    config_de_plantilla,
    config_vacia,
    normalizar_config,
    variables_disponibles,
)
from ..models import MotivoTramite, PlantillaTramite
from ..plantillas_utils import (
    es_administrador,
    extraer_variables_docx,
    guardar_docx_subido,
    resolver_docx,
)

_VARIABLE_VALIDA = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def administrador_requerido(vista):
    """Restringe la vista al grupo ADMINISTRADOR (o superusuario)."""

    @wraps(vista)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not es_administrador(request.user):
            raise PermissionDenied(
                'Solo el grupo ADMINISTRADOR puede gestionar plantillas.')
        return vista(request, *args, **kwargs)

    return _wrapped


def _config_inicial_usuario():
    config = config_vacia()
    config['campos'] = ['maestro_titular', 'folio', 'observaciones']
    config['requeridos'] = ['maestro_titular']
    config['mostrar_motivo'] = True
    config['motivos'] = []
    return config


def _url_generacion(plantilla):
    nombre = ('generar_oficios' if plantilla.tipo_documento == 'OFICIO'
              else 'generar_tramites_generales')
    return f"{reverse(nombre)}?plantilla={plantilla.pk}"


def _contexto_editor(plantilla, config, personalizados=None, errores=None,
                     valores=None):
    """Contexto compartido por alta y edición de plantillas."""
    config = normalizar_config(config or {})
    personalizados = personalizados if personalizados is not None else (
        config.get('campos_personalizados') or [])
    personalizados = [
        dict(
            campo,
            opciones_texto='\n'.join(campo.get('opciones') or []),
            tipo_texto=TIPOS_CAMPO_PERSONALIZADO.get(
                campo.get('tipo'), campo.get('tipo') or 'Texto'),
        )
        for campo in personalizados
    ]
    detectadas = list(getattr(plantilla, 'variables_detectadas', []) or [])
    catalogo = {fila['variable'] for fila in variables_disponibles()}
    seleccionadas = set(config.get('campos') or [])
    variables_campos = set()
    for clave in seleccionadas:
        info = CATALOGO_CAMPOS.get(clave) or {}
        variables_campos.update(info.get('variables') or [])

    return {
        'plantilla': plantilla,
        'config': config,
        'secciones_formulario': campos_por_seccion(),
        'tipos_campo': TIPOS_CAMPO_PERSONALIZADO.items(),
        'motivos': MotivoTramite.objects.order_by('motivo_tramite'),
        'personalizados': personalizados,
        'variables_detectadas': detectadas,
        'variables_catalogo': variables_disponibles(),
        'variables_no_reconocidas': sorted(
            set(detectadas) - catalogo, key=lambda v: v.lower()),
        'variables_sin_detectar': sorted(
            variables_campos - set(detectadas), key=lambda v: v.lower()),
        'errores': errores or [],
        'valores': valores or {},
        'campos_solo_lectura': CAMPOS_SOLO_LECTURA,
        'url_generacion': _url_generacion(plantilla),
        'es_sistema': bool(plantilla.es_sistema),
    }


def _leer_config_post(request):
    """Construye la configuración a partir del formulario del diseñador."""
    errores = []
    campos = [
        campo for campo in request.POST.getlist('campos')
        if campo in CATALOGO_CAMPOS
    ]
    # Sin repetidos y conservando el orden del catálogo elegido.
    campos = list(dict.fromkeys(campos))
    requeridos = [
        campo for campo in request.POST.getlist('requeridos')
        if campo in campos and campo not in CAMPOS_SOLO_LECTURA
    ]
    requeridos = list(dict.fromkeys(requeridos))

    mostrar_motivo = request.POST.get('mostrar_motivo') == 'on'
    motivos = []
    if mostrar_motivo:
        for valor in request.POST.getlist('motivos'):
            if str(valor).isdigit():
                motivos.append(int(valor))
        motivos = sorted(set(motivos))

    motivo_auto = (request.POST.get('motivo_auto') or '').strip()
    motivo_auto = int(motivo_auto) if motivo_auto.isdigit() else None
    if motivo_auto is not None:
        if not mostrar_motivo:
            errores.append('Para fijar un motivo automático, activa "Mostrar motivo".')
        elif motivos and motivo_auto not in motivos:
            motivos.append(motivo_auto)

    personalizados = []
    variables = request.POST.getlist('custom_variable')
    etiquetas = request.POST.getlist('custom_etiqueta')
    tipos = request.POST.getlist('custom_tipo')
    ayudas = request.POST.getlist('custom_ayuda')
    opciones = request.POST.getlist('custom_opciones')
    requeridos_custom = set(request.POST.getlist('custom_requerido'))
    vistas = set()

    for indice, datos in enumerate(itertools.zip_longest(
            variables, etiquetas, tipos, ayudas, opciones, fillvalue='')):
        variable, etiqueta, tipo, ayuda, opciones_texto = datos
        variable = (variable or '').strip()
        if not variable:
            continue
        if not _VARIABLE_VALIDA.match(variable):
            errores.append(
                f'La variable "{variable}" no es válida. Usa letras, números '
                'y guion bajo, sin espacios ni acentos (ej. Numero_Oficio).')
            continue
        if variable.lower() in vistas:
            errores.append(f'La variable "{variable}" está repetida.')
            continue
        vistas.add(variable.lower())
        if tipo not in TIPOS_CAMPO_PERSONALIZADO:
            tipo = 'texto'
        lista_opciones = [
            opcion.strip()
            for opcion in re.split(r'[\n,;]+', opciones_texto or '')
            if opcion.strip()
        ]
        if tipo == 'opciones' and not lista_opciones:
            errores.append(
                f'El campo "{etiqueta or variable}" necesita al menos una opción.')
        personalizados.append({
            'variable': variable,
            'etiqueta': (etiqueta or '').strip() or variable.replace('_', ' '),
            'tipo': tipo,
            'ayuda': (ayuda or '').strip(),
            'requerido': str(indice) in requeridos_custom,
            'opciones': lista_opciones,
        })

    if not campos and not personalizados:
        errores.append('Marca al menos un campo para el formulario.')

    config = config_vacia()
    config.update({
        'campos': campos,
        'requeridos': requeridos,
        'motivos': motivos,
        'mostrar_motivo': mostrar_motivo,
        'motivo_auto': motivo_auto,
        'calcular_antiguedad': request.POST.get('calcular_antiguedad') == 'on',
        'campos_personalizados': personalizados,
    })
    return config, errores


@administrador_requerido
def lista_plantillas(request):
    busqueda = (request.GET.get('q') or '').strip()
    tipo = (request.GET.get('tipo') or '').strip().upper()
    estado = (request.GET.get('estado') or '').strip()

    plantillas = PlantillaTramite.objects.all()
    if busqueda:
        plantillas = plantillas.filter(
            Q(nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda)
        )
    if tipo in ('TRAMITE', 'OFICIO'):
        plantillas = plantillas.filter(tipo_documento=tipo)
    if estado == 'activas':
        plantillas = plantillas.filter(activa=True)
    elif estado == 'inactivas':
        plantillas = plantillas.filter(activa=False)

    plantillas = plantillas.order_by('-es_sistema', 'nombre')
    return render(request, 'gestion_escolar/plantillas/lista_plantillas.html', {
        'titulo': 'Plantillas',
        'plantillas': plantillas,
        'busqueda': busqueda,
        'tipo': tipo,
        'estado': estado,
        'total_sistema': PlantillaTramite.objects.filter(es_sistema=True).count(),
        'total_usuario': PlantillaTramite.objects.filter(es_sistema=False).count(),
    })


@administrador_requerido
def crear_plantilla(request):
    if request.method == 'POST':
        nombre = (request.POST.get('nombre') or '').strip().upper()
        tipo = (request.POST.get('tipo_documento') or 'TRAMITE').strip().upper()
        descripcion = (request.POST.get('descripcion') or '').strip()
        errores = []

        if not nombre:
            errores.append('Escribe un nombre para la plantilla.')
        if tipo not in ('TRAMITE', 'OFICIO'):
            errores.append('Selecciona el tipo de documento.')
        if nombre and PlantillaTramite.objects.filter(
                nombre__iexact=nombre).exists():
            errores.append(f'Ya existe una plantilla con el nombre "{nombre}".')

        archivo = request.FILES.get('archivo_docx')
        if not archivo:
            errores.append('Selecciona el archivo .docx de la plantilla.')

        ruta = None
        ruta_absoluta = None
        if not errores:
            try:
                ruta, ruta_absoluta = guardar_docx_subido(archivo, nombre)
            except ValueError as exc:
                errores.append(str(exc))

        if errores:
            for error in errores:
                messages.error(request, error)
            return render(
                request, 'gestion_escolar/plantillas/nueva_plantilla.html', {
                    'titulo': 'Nueva plantilla',
                    'valores': {
                        'nombre': nombre,
                        'tipo_documento': tipo,
                        'descripcion': descripcion,
                    },
                })

        detectadas, advertencias = extraer_variables_docx(ruta_absoluta)
        plantilla = PlantillaTramite.objects.create(
            nombre=nombre,
            tipo_documento=tipo,
            descripcion=descripcion,
            ruta_archivo=ruta,
            es_sistema=False,
            activa=True,
            configuracion=_config_inicial_usuario(),
            variables_detectadas=detectadas,
        )
        messages.success(
            request,
            f'Plantilla "{plantilla.nombre}" creada. Ahora elige los datos '
            'que debe pedir el formulario.')
        for advertencia in advertencias:
            messages.warning(request, advertencia)
        return redirect('editar_plantilla', pk=plantilla.pk)

    return render(request, 'gestion_escolar/plantillas/nueva_plantilla.html', {
        'titulo': 'Nueva plantilla',
        'valores': {},
    })


@administrador_requerido
def editar_plantilla(request, pk):
    plantilla = get_object_or_404(PlantillaTramite, pk=pk)

    if plantilla.es_sistema:
        messages.info(
            request,
            'Esta plantilla es parte de la base del sistema: puedes '
            'consultarla y probarla, pero no editarla. Para hacer cambios, '
            'usa "Duplicar".')
        return render(
            request, 'gestion_escolar/plantillas/editar_plantilla.html',
            _contexto_editor(plantilla, config_de_plantilla(plantilla))
        )

    if request.method == 'POST':
        errores = []
        nombre = (request.POST.get('nombre') or '').strip().upper()
        tipo = (request.POST.get('tipo_documento') or 'TRAMITE').strip().upper()
        descripcion = (request.POST.get('descripcion') or '').strip()

        if not nombre:
            errores.append('Escribe un nombre para la plantilla.')
        elif PlantillaTramite.objects.filter(
                nombre__iexact=nombre).exclude(pk=plantilla.pk).exists():
            errores.append(f'Ya existe otra plantilla con el nombre "{nombre}".')
        if tipo not in ('TRAMITE', 'OFICIO'):
            errores.append('Selecciona el tipo de documento.')

        config, errores_config = _leer_config_post(request)
        errores.extend(errores_config)

        archivo = request.FILES.get('archivo_docx')
        ruta_nueva = None
        ruta_absoluta = None
        if archivo:
            try:
                ruta_nueva, ruta_absoluta = guardar_docx_subido(archivo, nombre or plantilla.nombre)
            except ValueError as exc:
                errores.append(str(exc))

        if errores:
            for error in errores:
                messages.error(request, error)
            personalizados = config.get('campos_personalizados') or []
            contexto = _contexto_editor(
                plantilla, config, personalizados=personalizados,
                errores=errores,
                valores={
                    'nombre': nombre,
                    'tipo_documento': tipo,
                    'descripcion': descripcion,
                })
            return render(
                request, 'gestion_escolar/plantillas/editar_plantilla.html',
                contexto)

        plantilla.nombre = nombre
        plantilla.tipo_documento = tipo
        plantilla.descripcion = descripcion
        plantilla.configuracion = config
        if ruta_nueva:
            plantilla.ruta_archivo = ruta_nueva
            variables, advertencias = extraer_variables_docx(ruta_absoluta)
            plantilla.variables_detectadas = variables
            for advertencia in advertencias:
                messages.warning(request, advertencia)
        plantilla.save()

        messages.success(request, f'Plantilla "{plantilla.nombre}" guardada.')
        return redirect('editar_plantilla', pk=plantilla.pk)

    return render(
        request, 'gestion_escolar/plantillas/editar_plantilla.html',
        _contexto_editor(plantilla, config_de_plantilla(plantilla)))


@administrador_requerido
@require_POST
def duplicar_plantilla(request, pk):
    origen = get_object_or_404(PlantillaTramite, pk=pk)
    base = f'{origen.nombre} COPIA'
    nombre = base[:100]
    contador = 2
    while PlantillaTramite.objects.filter(nombre__iexact=nombre).exists():
        sufijo = f' {contador}'
        nombre = f'{base[:100 - len(sufijo)]}{sufijo}'
        contador += 1

    config = normalizar_config(
        origen.configuracion or config_de_plantilla(origen))
    config['origen'] = 'usuario'
    nueva = PlantillaTramite.objects.create(
        nombre=nombre,
        ruta_archivo=origen.ruta_archivo,
        descripcion=origen.descripcion,
        tipo_documento=origen.tipo_documento,
        es_sistema=False,
        activa=True,
        configuracion=config,
        variables_detectadas=origen.variables_detectadas or [],
    )
    messages.success(
        request,
        f'Se creó "{nueva.nombre}" como copia editable de "{origen.nombre}".')
    return redirect('editar_plantilla', pk=nueva.pk)


@administrador_requerido
@require_POST
def alternar_activa(request, pk):
    plantilla = get_object_or_404(PlantillaTramite, pk=pk)
    if plantilla.es_sistema:
        messages.error(
            request,
            'Las plantillas del sistema se conservan siempre activas.')
        return redirect('lista_plantillas')
    plantilla.activa = not plantilla.activa
    plantilla.save(update_fields=['activa'])
    estado = 'activada' if plantilla.activa else 'desactivada'
    messages.success(request, f'Plantilla "{plantilla.nombre}" {estado}.')
    return redirect('lista_plantillas')


@administrador_requerido
@require_POST
def eliminar_plantilla(request, pk):
    plantilla = get_object_or_404(PlantillaTramite, pk=pk)
    if plantilla.es_sistema:
        messages.error(
            request,
            'Las plantillas del sistema no se pueden eliminar.')
        return redirect('editar_plantilla', pk=pk)
    nombre = plantilla.nombre
    plantilla.delete()
    messages.success(request, f'Plantilla "{nombre}" eliminada.')
    return redirect('lista_plantillas')


@administrador_requerido
def probar_plantilla(request, pk):
    plantilla = get_object_or_404(PlantillaTramite, pk=pk)
    return redirect(_url_generacion(plantilla))


@administrador_requerido
@require_POST
def analizar_variables(request, pk):
    plantilla = get_object_or_404(PlantillaTramite, pk=pk)
    ruta = resolver_docx(plantilla.ruta_archivo)
    if not ruta:
        messages.error(
            request,
            'No se encontró el archivo .docx de esta plantilla. '
            'Vuelve a subirlo desde la edición.')
        return redirect('editar_plantilla', pk=pk)
    variables, advertencias = extraer_variables_docx(ruta)
    plantilla.variables_detectadas = variables
    plantilla.save(update_fields=['variables_detectadas'])
    messages.success(
        request,
        f'Se detectaron {len(variables)} variable(s) en el documento.')
    for advertencia in advertencias:
        messages.warning(request, advertencia)
    return redirect('editar_plantilla', pk=pk)
