from django.db import migrations

def corregir_ruta(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    PlantillaTramite.objects.filter(nombre='PRESENTACION LABORAL PARA CAMBIO DE ADSCRIPCION').update(
        ruta_archivo='gestion_escolar/templates/tramites/Plantillas/Word/PRESENTACIONLABORALPORCAMBIOS.docx'
    )

class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0058_corregir_nombre_plantilla_adscripcion'),
    ]

    operations = [
        migrations.RunPython(corregir_ruta, migrations.RunPython.noop),
    ]
