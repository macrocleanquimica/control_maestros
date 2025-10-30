from django import template
from gestion_escolar.models import Maestro, MotivoTramite, PlantillaTramite

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Permite acceder a un valor de diccionario usando una variable como clave en las plantillas.
    Uso: {{ mi_diccionario|get_item:mi_variable_de_clave }}
    """
    return dictionary.get(key)

@register.filter(name='get_maestro_by_id')
def get_maestro_by_id(maestro_id):
    try:
        return Maestro.objects.get(pk=maestro_id)
    except Maestro.DoesNotExist:
        return f"Maestro no encontrado (ID: {maestro_id})"

@register.filter(name='get_motivo_by_id')
def get_motivo_by_id(motivo_id):
    try:
        return MotivoTramite.objects.get(pk=motivo_id)
    except MotivoTramite.DoesNotExist:
        return f"Motivo no encontrado (ID: {motivo_id})"

@register.filter(name='get_plantilla_by_id')
def get_plantilla_by_id(plantilla_id):
    try:
        return PlantillaTramite.objects.get(pk=plantilla_id)
    except PlantillaTramite.DoesNotExist:
        return f"Plantilla no encontrada (ID: {plantilla_id})"

@register.filter(name='startswith')
def startswith(text, starts):
    """
    Devuelve True si el texto comienza con la cadena especificada.
    """
    if isinstance(text, str):
        return text.startswith(starts)
    return False

@register.filter(name='replace')
def replace(value, arg):
    """
    Reemplaza una subcadena por otra.
    Uso: {{ "hola_mundo"|replace:"_, " }} -> "hola mundo"
    """
    return value.replace(arg, ' ')

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Verifica si un usuario pertenece a un grupo específico.
    Uso: {% if user|has_group:"Directores" %}
    """
    return user.groups.filter(name=group_name).exists()

@register.filter(name='has_group')
def has_group(user, group_name):
    """
    Verifica si un usuario pertenece a un grupo específico.
    Uso: {% if user|has_group:"Directores" %}
    """
    return user.groups.filter(name=group_name).exists()