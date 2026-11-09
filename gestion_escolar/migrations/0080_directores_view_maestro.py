from django.db import migrations


def otorgar_view_maestro_directores(apps, schema_editor):
    """El Director solo debe ver el personal de su escuela: le da view_maestro.

    Con este permiso aparece el menú Personal; el alcance por escuela lo
    aplican las vistas (lista/detalle/buscadores). No recibe trámites,
    historial, kardex, FUP ni ningún otro permiso.
    """
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    grupo, _ = Group.objects.get_or_create(name='Directores')
    try:
        perm = Permission.objects.get(codename='view_maestro')
    except Permission.DoesNotExist:
        return
    grupo.permissions.add(perm)


def revertir_sin_cambios(apps, schema_editor):
    # Reversa intencionalmente vacía: no quitar permisos al revertir.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0079_alter_escuela_zona_esc_alter_escuelaregular_cct_and_more'),
    ]

    operations = [
        migrations.RunPython(otorgar_view_maestro_directores, revertir_sin_cambios),
    ]
