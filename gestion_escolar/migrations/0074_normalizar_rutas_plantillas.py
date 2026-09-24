# Normaliza PlantillaTramite.ruta_archivo a rutas relativas portables
# dentro de la carpeta canónica:
#   gestion_escolar/templates/tramites/Plantillas/Word/<archivo>
# Reversible: no-op (las rutas viejas absolutas C:\ ya no se restauran).
import os

from django.db import migrations


CANONICA = os.path.join(
    'gestion_escolar', 'templates', 'tramites', 'Plantillas', 'Word')


def normalizar_rutas(apps, schema_editor):
    PlantillaTramite = apps.get_model('gestion_escolar', 'PlantillaTramite')
    for plantilla in PlantillaTramite.objects.all():
        nombre_archivo = os.path.basename(str(plantilla.ruta_archivo or ''))
        if not nombre_archivo:
            continue
        nueva = os.path.join(CANONICA, nombre_archivo)
        if plantilla.ruta_archivo != nueva:
            plantilla.ruta_archivo = nueva
            plantilla.save(update_fields=['ruta_archivo'])


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0073_zona_nombre_alter_lotereportevacancia_estado'),
    ]

    operations = [
        migrations.RunPython(normalizar_rutas, migrations.RunPython.noop),
    ]
