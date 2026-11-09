from django.db import migrations


def otorgar_tema_administrador(apps, schema_editor):
    """Da los permisos de Temas al ADMINISTRADOR (ya visibles en la matriz).

    Antes nadie los tenía: solo el superusuario podía gestionar temas.
    """
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    try:
        grupo = Group.objects.get(name='ADMINISTRADOR')
    except Group.DoesNotExist:
        return
    perms = Permission.objects.filter(
        codename__in=['view_tema', 'add_tema', 'change_tema', 'delete_tema'],
        content_type__app_label='gestion_escolar',
    )
    grupo.permissions.add(*perms)


def revertir_sin_cambios(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0080_directores_view_maestro'),
    ]

    operations = [
        migrations.RunPython(otorgar_tema_administrador, revertir_sin_cambios),
    ]
