from django.db import migrations

def crear_plantilla(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    PlantillaTramite.objects.create(
        nombre='SOLICITUD BECA COMISION',
        ruta_archivo='gestion_escolar/templates/tramites/Plantillas/Word/SOLICITUDBECACOMISION.docx',
        tipo_documento='OFICIO'
    )

class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0059_corregir_ruta_plantilla_adscripcion'),
    ]

    operations = [
        migrations.RunPython(crear_plantilla, migrations.RunPython.noop),
    ]
