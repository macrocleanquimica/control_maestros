from django.db import migrations

def corregir_nombre(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    PlantillaTramite.objects.filter(nombre='PRESENTACION LABORAL PARA CAMBIO DE ADCRIPCION').update(
        nombre='PRESENTACION LABORAL PARA CAMBIO DE ADSCRIPCION'
    )

class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0057_crear_plantilla_presentacion_cambio_adscripcion'),
    ]

    operations = [
        migrations.RunPython(corregir_nombre, migrations.RunPython.noop),
    ]
