import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Maestro

def update_funciones_v4():
    incorrect_name = "MAESTRO ESPECIALISTA DOCENTE DE APOYO"
    correct_name = "MAESTRO(A) ESPECIALISTA DOCENTE DE APOYO"
    
    count = Maestro.objects.filter(funcion=incorrect_name).count()
    print(f"Found {count} records with function '{incorrect_name}'")
    
    if count > 0:
        updated = Maestro.objects.filter(funcion=incorrect_name).update(funcion=correct_name)
        print(f"Updated {updated} records to '{correct_name}'")

if __name__ == '__main__':
    update_funciones_v4()
