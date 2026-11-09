"""Utilidades del diseñador de plantillas.

- Detecta las variables ``{{ ... }}`` de un .docx (incluidas las que Word
  partió entre varios runs).
- Valida y guarda los .docx subidos dentro de la carpeta canónica.
- Comprueba si un usuario pertenece al grupo ADMINISTRADOR.
"""

import os
import re
import unicodedata
import zipfile
from xml.etree import ElementTree

from django.conf import settings

PLANTILLAS_WORD_DIR = os.path.join(
    str(settings.BASE_DIR), 'gestion_escolar', 'templates', 'tramites',
    'Plantillas', 'Word',
)
REL_PLANTILLAS_WORD_DIR = 'gestion_escolar/templates/tramites/Plantillas/Word'

_W_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
_VARIABLE_RE = re.compile(r'\{\{\s*([^{}]+?)\s*\}\}')
_PARTES_DOCX = ('word/document.xml',)


def es_administrador(user):
    """Solo el grupo ADMINISTRADOR (o un superusuario) gestiona plantillas."""
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    try:
        return user.groups.filter(name='ADMINISTRADOR').exists()
    except Exception:
        return False


def _texto_de_parrafo(parrafo):
    """Une el texto de todos los runs del párrafo, respetando el orden."""
    return ''.join(
        nodo.text or ''
        for nodo in parrafo.iter()
        if nodo.tag == _W_NS + 't'
    )


def _partes_docx(archivo_zip):
    """Partes del .docx donde puede haber variables."""
    nombres = set(archivo_zip.namelist())
    partes = [parte for parte in _PARTES_DOCX if parte in nombres]
    for nombre in sorted(nombres):
        if re.match(r'word/(header|footer)\d*\.xml$', nombre):
            partes.append(nombre)
    return partes


def extraer_variables_docx(ruta_o_archivo):
    """Devuelve las variables de un .docx y avisos de variables partidas.

    Retorna ``(variables, advertencias)``:
    - ``variables``: lista ordenada y sin repetir.
    - ``advertencias``: lista de textos para mostrar en el diseñador.
    """
    variables = set()
    advertencias = []
    try:
        with zipfile.ZipFile(ruta_o_archivo) as archivo_zip:
            partes = _partes_docx(archivo_zip)
            if not partes:
                return [], ['El archivo no parece un documento de Word válido.']
            for parte in partes:
                try:
                    raiz = ElementTree.fromstring(archivo_zip.read(parte))
                except ElementTree.ParseError:
                    advertencias.append(f'No se pudo leer una parte del documento ({parte}).')
                    continue
                for parrafo in raiz.iter(_W_NS + 'p'):
                    texto = _texto_de_parrafo(parrafo)
                    encontradas = _VARIABLE_RE.findall(texto)
                    if not encontradas:
                        continue
                    variables.update(v.strip() for v in encontradas if v.strip())
                    # Si la variable no se encuentra dentro de un solo run es
                    # porque Word la partió; docxtpl podría no reemplazarla.
                    runs = [
                        nodo.text or ''
                        for nodo in parrafo.iter()
                        if nodo.tag == _W_NS + 't'
                    ]
                    por_run = set()
                    for texto_run in runs:
                        por_run.update(_VARIABLE_RE.findall(texto_run))
                    partidas = [v for v in encontradas if v.strip() not in por_run]
                    if partidas and parte == 'word/document.xml':
                        advertencias.append(
                            'Word dividió la variable '
                            + ', '.join(f'{{{{ {v.strip()} }}}}' for v in sorted(set(partidas)))
                            + '. Si el documento no se llena, vuelve a escribirla de un tirón.'
                        )
    except zipfile.BadZipFile:
        return [], ['El archivo no es un .docx válido (no es un ZIP de Word).']
    except FileNotFoundError:
        return [], ['No se encontró el archivo de la plantilla.']
    except Exception as exc:
        return [], [f'No se pudieron leer las variables: {exc}']

    return sorted(variables, key=lambda v: v.lower()), list(dict.fromkeys(advertencias))


def _nombre_archivo_seguro(nombre):
    base = os.path.splitext(os.path.basename(nombre or ''))[0]
    base = unicodedata.normalize('NFKD', base).encode('ascii', 'ignore').decode('ascii')
    base = base.replace(' ', '_')
    base = re.sub(r'[^A-Za-z0-9_-]+', '', base).upper()
    return (base or 'PLANTILLA')[:80]


def _ruta_libre(directorio, base, extension='.docx'):
    candidato = os.path.join(directorio, base + extension)
    contador = 2
    while os.path.exists(candidato):
        candidato = os.path.join(directorio, f'{base}_{contador}{extension}')
        contador += 1
    return candidato


def guardar_docx_subido(archivo, nombre_plantilla):
    """Valida y guarda un .docx en la carpeta canónica.

    Devuelve ``(ruta_relativa, ruta_absoluta)`` o lanza ``ValueError`` con un
    mensaje entendible para el usuario.
    """
    if archivo is None:
        raise ValueError('Selecciona un archivo .docx.')
    nombre = getattr(archivo, 'name', '') or ''
    if not nombre.lower().endswith('.docx'):
        raise ValueError('El archivo debe ser un documento de Word (.docx).')
    if archivo.size > 15 * 1024 * 1024:
        raise ValueError('El archivo es demasiado grande (máximo 15 MB).')
    if not zipfile.is_zipfile(archivo):
        raise ValueError('El archivo no es un .docx válido.')

    # Rebobinar y comprobar que tiene la estructura mínima.
    try:
        archivo.seek(0)
        with zipfile.ZipFile(archivo) as archivo_zip:
            if 'word/document.xml' not in archivo_zip.namelist():
                raise ValueError('El archivo no contiene el documento de Word esperado.')
    except zipfile.BadZipFile:
        raise ValueError('El archivo no es un .docx válido.')
    finally:
        try:
            archivo.seek(0)
        except Exception:
            pass

    os.makedirs(PLANTILLAS_WORD_DIR, exist_ok=True)
    base = _nombre_archivo_seguro(nombre_plantilla or nombre)
    destino = _ruta_libre(PLANTILLAS_WORD_DIR, base)
    with open(destino, 'wb+') as salida:
        for chunk in archivo.chunks():
            salida.write(chunk)
    ruta_relativa = f'{REL_PLANTILLAS_WORD_DIR}/{os.path.basename(destino)}'
    return ruta_relativa, destino


def resolver_docx(ruta):
    """Resuelve la ruta de una plantilla para leerla (misma lógica del motor)."""
    if not ruta:
        return None
    if os.path.isabs(ruta) and os.path.exists(ruta):
        return ruta
    candidato = os.path.join(str(settings.BASE_DIR), ruta)
    if os.path.exists(candidato):
        return candidato
    nombre = os.path.basename(ruta)
    candidato = os.path.join(PLANTILLAS_WORD_DIR, nombre)
    return candidato if os.path.exists(candidato) else None


def json_para_js(valor):
    """Serializa datos para incrustarlos dentro de un <script>."""
    import json
    return (
        json.dumps(valor, ensure_ascii=False)
        .replace('<', '\\u003c')
        .replace('>', '\\u003e')
        .replace('&', '\\u0026')
    )
