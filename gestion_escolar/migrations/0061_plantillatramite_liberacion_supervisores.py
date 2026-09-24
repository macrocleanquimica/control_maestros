from django.db import migrations

def crear_plantilla(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    PlantillaTramite.objects.create(
        nombre='LIBERACION DE SUPERVISORES',
        ruta_archivo='gestion_escolar/templates/tramites/Plantillas/Word/LIBERACIONSUPERVISORES.docx',
        tipo_documento='OFICIO'
    )

class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0060_plantillatramite_solicitud_beca_comision'),
    ]

    operations = [
        migrations.RunPython(crear_plantilla, migrations.RunPython.noop),
    ]
