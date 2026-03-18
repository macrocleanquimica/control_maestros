import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Incentivo

incentivos = [
    '7A', '7B', '7C', '7D', 'K1', 'K1A', 'K1B', 'K1C', 'KR', 'K4C', 'A1', '1B', 'KU', 'O1'
]

for codigo in incentivos:
    Incentivo.objects.get_or_create(codigo=codigo)

print(f"Se han cargado {len(incentivos)} incentivos correctamente.")
