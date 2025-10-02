from django import template
from gestion_escolar.models import Maestro, MotivoTramite, PlantillaTramite

register = template.Library()

@register.filter
def get_maestro_by_id(maestro_id):
    try:
        maestro = Maestro.objects.get(id_maestro=maestro_id)
        return str(maestro) # Or maestro.get_full_name() if available
    except Maestro.DoesNotExist:
        return f"Maestro no encontrado (ID: {maestro_id})"
    except Exception:
        return f"Error al obtener Maestro (ID: {maestro_id})"

@register.filter
def get_motivo_by_id(motivo_id):
    try:
        motivo = MotivoTramite.objects.get(id=motivo_id)
        return motivo.motivo_tramite
    except MotivoTramite.DoesNotExist:
        return f"Motivo no encontrado (ID: {motivo_id})"
    except Exception:
        return f"Error al obtener Motivo (ID: {motivo_id})"

@register.filter
def get_plantilla_by_id(plantilla_id):
    try:
        plantilla = PlantillaTramite.objects.get(id=plantilla_id)
        return plantilla.nombre
    except PlantillaTramite.DoesNotExist:
        return f"Plantilla no encontrada (ID: {plantilla_id})"
    except Exception:
        return f"Error al obtener Plantilla (ID: {plantilla_id})"

@register.filter
def startswith(value, arg):
    """Checks if a string starts with the given argument."""
    return value.startswith(arg)

@register.filter
def replace(value, arg):
    """Replaces all occurrences of a substring with another substring."""
    if isinstance(value, str) and isinstance(arg, str) and '|' in arg:
        old, new = arg.split('|', 1)
        return value.replace(old, new)
    return value