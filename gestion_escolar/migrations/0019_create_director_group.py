from django.db import migrations

def create_director_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='Directores')

class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0018_documentoexpediente'),
    ]

    operations = [
        migrations.RunPython(create_director_group),
    ]