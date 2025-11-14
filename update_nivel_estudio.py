
import os
import django
from django.db.models.functions import Upper

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Maestro

print("Actualizando niveles de estudio a mayúsculas...")
updated_count = Maestro.objects.update(nivel_estudio=Upper('nivel_estudio'))
print(f"{updated_count} registros actualizados.")
