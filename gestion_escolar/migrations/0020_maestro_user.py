from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gestion_escolar', '0019_create_director_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='maestro',
            name='user',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='maestro_profile', to=settings.AUTH_USER_MODEL),
        ),
    ]