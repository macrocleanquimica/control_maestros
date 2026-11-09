# Registra el trámite ALTA PROVISIONAL EN VACANTE DEFINITIVA (99):
#   - PlantillaTramite que apunta a ALTAPROVISIONALENVACANTEDEFINITIVA.docx
#   - MotivoTramite propio, que el formulario oculta y el backend fuerza.
# Reversible: elimina ambos registros.
import os

from django.db import migrations

NOMBRE_PLANTILLA = 'ALTA PROVISIONAL EN VACANTE DEFINITIVA (99)'
MOTIVO = 'ALTA PROVISIONAL EN VACANTE DEFINITIVA (99)'
ARCHIVO = 'ALTAPROVISIONALENVACANTEDEFINITIVA.docx'
CANONICA = os.path.join(
    'gestion_escolar', 'templates', 'tramites', 'Plantillas', 'Word')


def crear(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    MotivoTramite = apps.get_model('gestion_escolar', 'MotivoTramite')

    PlantillaTramite.objects.get_or_create(
        nombre=NOMBRE_PLANTILLA,
        defaults={
            'ruta_archivo': os.path.join(CANONICA, ARCHIVO),
            'tipo_documento': 'TRAMITE',
        },
    )
    MotivoTramite.objects.get_or_create(motivo_tramite=MOTIVO)


def revertir(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    MotivoTramite = apps.get_model('gestion_escolar', 'MotivoTramite')
    PlantillaTramite.objects.filter(nombre=NOMBRE_PLANTILLA).delete()
    MotivoTramite.objects.filter(motivo_tramite=MOTIVO).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0075_tema_color_boton'),
    ]

    operations = [
        migrations.RunPython(crear, revertir),
    ]