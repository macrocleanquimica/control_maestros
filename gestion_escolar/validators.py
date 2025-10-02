# gestion_escolar/validators.py
import re
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