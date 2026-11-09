"""Migra las plantillas existentes a la configuración del diseñador.

Las 23 plantillas que ya funcionaban quedan marcadas como ``es_sistema`` y
reciben la misma configuración de campos, motivos y opciones que hoy está en
el código. No se borra ni se altera ningún dato de los trámites existentes.
"""

from django.db import migrations


def configurar_plantillas(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    from gestion_escolar.campos_plantilla import (
        PLANTILLAS_SISTEMA, config_sistema, normalizar_nombre,
    )

    canonicos = {normalizar_nombre(nombre): nombre for nombre in PLANTILLAS_SISTEMA}

    for plantilla in PlantillaTramite.objects.all():
        canonico = canonicos.get(normalizar_nombre(plantilla.nombre))
        if canonico is None:
            # Nombre desconocido: se deja editable y con una configuración
            # mínima para que no quede inutilizable.
            if not plantilla.configuracion:
                plantilla.configuracion = {
                    'version': 1,
                    'origen': 'usuario',
                    'campos': ["maestro_titular", "folio", "observaciones"],
                    'requeridos': ["maestro_titular"],
                    'motivos': [],
                    'mostrar_motivo': True,
                    'motivo_auto': None,
                    'calcular_antiguedad': False,
                    'usa_variante_desubicado': False,
                    'campos_personalizados': [],
                }
                plantilla.save(update_fields=['configuracion'])
            continue

        if not plantilla.configuracion:
            plantilla.configuracion = config_sistema(canonico)
        plantilla.es_sistema = True
        plantilla.activa = True
        plantilla.save(update_fields=['configuracion', 'es_sistema', 'activa'])


def revertir(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    PlantillaTramite.objects.update(es_sistema=False, activa=True)


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0083_plantillatramite_disennador'),
    ]

    operations = [
        migrations.RunPython(configurar_plantillas, revertir),
    ]
