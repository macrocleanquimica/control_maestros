# gestion_escolar/validators.py
import re
from datetime import date

from django.core.exceptions import ValidationError

def validate_cct_format(value):
    """
    Valida que el CCT tenga el formato correcto: 2 dígitos + 3 letras + 4 dígitos + 1 letra
    Ejemplo: 10DML0013Q
    """
    pattern = re.compile(r'^\d{2}[A-Z]{3}\d{4}[A-Z]$')
    if not pattern.match(value):
        raise ValidationError(
            'Formato de CCT inválido. Debe ser: 2 dígitos + 3 letras + 4 dígitos + 1 letra (ej: 10DML0013Q)'
        )


# ---------------------------------------------------------------------------
# CURP / RFC (validación estructural local, sin consulta a RENAPO/SAT)
# ---------------------------------------------------------------------------

# Diccionario oficial usado por los algoritmos de dígito verificador.
_DICCIONARIO = '0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ'

# Claves de entidad federativa válidas en la CURP (incluye NE para nacidos
# en el extranjero).
ENTIDADES_CURP = frozenset({
    'AS', 'BC', 'BS', 'CC', 'CL', 'CM', 'CS', 'CH', 'DF', 'DG',
    'GT', 'GR', 'HG', 'JC', 'MC', 'MN', 'MS', 'NT', 'NL', 'OC',
    'PL', 'QT', 'QR', 'SP', 'SL', 'SR', 'TC', 'TS', 'TL', 'VZ',
    'YN', 'ZS', 'NE',
})

_CURP_RE = re.compile(r'^[A-ZÑ]{4}(\d{6})[HM]([A-Z]{2})([A-ZÑ]{3})([A-Z0-9])(\d)$')
_RFC_RE = re.compile(r'^[A-ZÑ]{4}(\d{6})([A-Z0-9]{2})([A-Z0-9])$')
_VOCALES = frozenset('AEIOU')


def normalizar_curp(value):
    """Mayúsculas y sin espacios. Devuelve '' si no hay valor."""
    return re.sub(r'\s+', '', str(value or '')).upper()


def normalizar_rfc(value):
    """Mayúsculas y sin espacios. Devuelve '' si no hay valor."""
    return re.sub(r'\s+', '', str(value or '')).upper()


def _fecha_valida(anio, mes, dia):
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def _fecha_aa_mm_dd(aa, mm, dd, siglo):
    return _fecha_valida(siglo + int(aa), int(mm), int(dd))


def _digito_verificador_curp(curp):
    suma = 0
    for indice, caracter in enumerate(curp[:17]):
        try:
            valor = _DICCIONARIO.index(caracter)
        except ValueError:
            return None
        suma += valor * (18 - indice)
    return (10 - (suma % 10)) % 10


def _digito_verificador_rfc(rfc):
    suma = 0
    for indice, caracter in enumerate(rfc[:12]):
        try:
            valor = _DICCIONARIO.index(caracter)
        except ValueError:
            return None
        suma += valor * (13 - indice)
    residuo = 11 - (suma % 11)
    if residuo == 11:
        return '0'
    if residuo == 10:
        return 'A'
    return str(residuo)


def fecha_nacimiento_desde_curp(value):
    """Devuelve la fecha de nacimiento que contiene la CURP, o None si no es
    posible determinarla. La centuria se infiere de la posición 17: dígito
    para nacidos antes de 2000, letra para nacidos a partir de 2000."""
    curp = normalizar_curp(value)
    if len(curp) != 18:
        return None
    coincidencia = _CURP_RE.match(curp)
    if not coincidencia:
        return None
    aa, mm, dd = coincidencia.group(1)[0:2], coincidencia.group(1)[2:4], coincidencia.group(1)[4:6]
    siglo = 1900 if curp[16].isdigit() else 2000
    return _fecha_aa_mm_dd(aa, mm, dd, siglo)


def prefijo_rfc_desde_curp(value):
    """Primeros 10 caracteres de la CURP (base del RFC persona física)."""
    curp = normalizar_curp(value)
    if len(curp) != 18:
        return ''
    return curp[:10]


def validar_curp(value):
    """Valida estructura, fecha, sexo, entidad, consonantes, homoclave y
    dígito verificador de una CURP. Un valor vacío se considera válido
    porque el campo es opcional."""
    curp = normalizar_curp(value)
    if not curp:
        return

    if len(curp) != 18:
        raise ValidationError('La CURP debe tener exactamente 18 caracteres.')

    coincidencia = _CURP_RE.match(curp)
    if not coincidencia:
        raise ValidationError(
            'La estructura de la CURP no es válida. Debe iniciar con 4 letras, '
            'seguir 6 dígitos de fecha, sexo H/M, 2 letras de entidad y 3 consonantes.'
        )

    fecha = fecha_nacimiento_desde_curp(curp)
    if fecha is None:
        raise ValidationError('La fecha de nacimiento contenida en la CURP no es válida.')
    if fecha > date.today():
        # La centuria se infiere de la posición 17. Si con la otra centuria la
        # fecha sí existe y no es futura, el problema real es la homoclave.
        aa, mm, dd = coincidencia.group(1)[0:2], coincidencia.group(1)[2:4], coincidencia.group(1)[4:6]
        siglo_alterno = 1900 if fecha.year >= 2000 else 2000
        fecha_alterna = _fecha_aa_mm_dd(aa, mm, dd, siglo_alterno)
        if fecha_alterna is not None and fecha_alterna <= date.today():
            raise ValidationError(
                'La posición 17 de la CURP no corresponde al año de nacimiento.'
            )
        raise ValidationError('La fecha de nacimiento de la CURP no puede ser futura.')

    entidad = coincidencia.group(2)
    if entidad not in ENTIDADES_CURP:
        raise ValidationError(
            f'El código de entidad federativa de la CURP ("{entidad}") no es válido.'
        )

    consonantes = coincidencia.group(3)
    if any(letra in _VOCALES for letra in consonantes):
        raise ValidationError(
            'Las posiciones 14 a 16 de la CURP deben ser consonantes internas.'
        )

    anio = fecha.year
    homoclave = coincidencia.group(4)
    if anio < 2000 and not homoclave.isdigit():
        raise ValidationError(
            'La posición 17 de la CURP debe ser un dígito para nacidos antes de 2000.'
        )
    if anio >= 2000 and not homoclave.isalpha():
        raise ValidationError(
            'La posición 17 de la CURP debe ser una letra para nacidos a partir de 2000.'
        )

    digito_calculado = _digito_verificador_curp(curp)
    if digito_calculado is None or str(digito_calculado) != curp[17]:
        raise ValidationError('El dígito verificador de la CURP no es válido.')


def validar_rfc(value):
    """Valida estructura, fecha y dígito verificador de un RFC persona física
    de 13 caracteres. Un valor vacío se considera válido porque el campo es
    opcional."""
    rfc = normalizar_rfc(value)
    if not rfc:
        return

    if len(rfc) != 13:
        raise ValidationError('El RFC debe tener exactamente 13 caracteres (persona física).')

    coincidencia = _RFC_RE.match(rfc)
    if not coincidencia:
        raise ValidationError(
            'La estructura del RFC no es válida. Debe tener 4 letras, 6 dígitos '
            'de fecha y 3 caracteres de homoclave.'
        )

    aa, mm, dd = coincidencia.group(1)[0:2], coincidencia.group(1)[2:4], coincidencia.group(1)[4:6]
    # El RFC no indica la centuria; se acepta si la fecha existe en 1900 o 2000.
    if _fecha_aa_mm_dd(aa, mm, dd, 1900) is None and _fecha_aa_mm_dd(aa, mm, dd, 2000) is None:
        raise ValidationError('La fecha de nacimiento contenida en el RFC no es válida.')

    digito_calculado = _digito_verificador_rfc(rfc)
    if digito_calculado is None or digito_calculado != rfc[12]:
        raise ValidationError('El dígito verificador del RFC no es válido.')


def es_curp_valida(value):
    try:
        validar_curp(value)
    except ValidationError:
        return False
    return True


def es_rfc_valido(value):
    try:
        validar_rfc(value)
    except ValidationError:
        return False
    return True