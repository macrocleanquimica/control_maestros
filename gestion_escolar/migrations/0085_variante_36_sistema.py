# Conserva la variante Art. 36 de la solicitud de asignación como plantilla
# del sistema (solo lectura), igual que las demás plantillas existentes.
from django.db import migrations

NOMBRE = 'SOLICITUD DE ASIGNACION 36'


def marcar_variante(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    from gestion_escolar.campos_plantilla import config_sistema

    for plantilla in PlantillaTramite.objects.filter(nombre__iexact=NOMBRE):
        if not plantilla.configuracion:
            plantilla.configuracion = config_sistema(NOMBRE)
        plantilla.es_sistema = True
        plantilla.activa = True
        plantilla.save(update_fields=['configuracion', 'es_sistema', 'activa'])


def revertir(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    PlantillaTramite.objects.filter(nombre__iexact=NOMBRE).update(es_sistema=False)


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0084_configurar_plantillas_sistema'),
    ]

    operations = [
        migrations.RunPython(marcar_variante, revertir),
    ]
