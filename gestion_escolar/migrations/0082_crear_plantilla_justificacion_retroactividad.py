# Registra el oficio JUSTIFICACION DE RETROACTIVIDAD:
#   - PlantillaTramite tipo OFICIO que apunta a JUSTIFICACIONRETROACTIVIDAD.docx
# Reversible: elimina el registro.
import os

from django.db import migrations

NOMBRE_PLANTILLA = 'JUSTIFICACION DE RETROACTIVIDAD'
ARCHIVO = 'JUSTIFICACIONRETROACTIVIDAD.docx'
CANONICA = os.path.join(
    'gestion_escolar', 'templates', 'tramites', 'Plantillas', 'Word')


def crear(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')

    PlantillaTramite.objects.get_or_create(
        nombre=NOMBRE_PLANTILLA,
        defaults={
            'ruta_archivo': os.path.join(CANONICA, ARCHIVO),
            'tipo_documento': 'OFICIO',
        },
    )


def revertir(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    PlantillaTramite.objects.filter(nombre=NOMBRE_PLANTILLA).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0081_tema_perms_administrador'),
    ]

    operations = [
        migrations.RunPython(crear, revertir),
    ]
