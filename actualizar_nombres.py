import os
import django
from unidecode import unidecode

# Configura el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Maestro

def actualizar_nombres_unaccented():
    print("Iniciando actualización de nombres sin acentos...")
    maestros = Maestro.objects.all()
    actualizados = 0
    for maestro in maestros:
        # Forzamos el re-guardado para que se ejecute el método save()
        maestro.save()
        actualizados += 1

    print(f"¡Actualización completada! Se procesaron {actualizados} maestros.")

if __name__ == "__main__":
    actualizar_nombres_unaccented()
