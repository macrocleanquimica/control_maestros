# Normaliza el campo `Maestro.status` a solo los estados ACTIVO / INACTIVO.
# Antes había variantes: 'ACTIVA' (6), 'ACTIVO ' (1), vacío (10), None (6),
# y subestados BAJA (3) / JUBILADO (1) que la lógica no distinguía.
# Decisión de negocio:
#   - 'ACTIVA' y 'ACTIVO ' -> 'ACTIVO'
#   - ''  y None           -> 'ACTIVO'
#   - 'BAJA' y 'JUBILADO'  -> 'INACTIVO'  (son subestados de inactivo)

from django.db import migrations


def normalizar_status(apps, schema_editor):
    Maestro = apps.get_model('gestion_escolar', 'Maestro')
    Maestro.objects.filter(status__in=['ACTIVA', 'ACTIVO ']).update(status='ACTIVO')
    Maestro.objects.filter(status='BAJA').update(status='INACTIVO')
    Maestro.objects.filter(status='JUBILADO').update(status='INACTIVO')
    Maestro.objects.filter(status='').update(status='ACTIVO')
    Maestro.objects.filter(status__isnull=True).update(status='ACTIVO')


def revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0064_eliminar_modelo_director'),
    ]

    operations = [
        migrations.RunPython(normalizar_status, revertir),
    ]