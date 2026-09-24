from django.db import migrations

def crear_plantilla(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    PlantillaTramite.objects.create(
        nombre='PRESENTACION LABORAL PARA CAMBIO DE ADCRIPCION',
        ruta_archivo='tramites/Plantillas/Word/PRESENTACIONLABORALPORCAMBIOS.docx',
        tipo_documento='OFICIO'
    )

class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0056_maestro_unique_maestro_completo'),
    ]

    operations = [
        migrations.RunPython(crear_plantilla, migrations.RunPython.noop),
    ]
