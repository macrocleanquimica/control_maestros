import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Maestro

def update_funciones_v2():
    # Incorrect function name (the one we just standardized to, or any remaining ones)
    target_incorrect = "MAESTRO(A) DE APOYO"
    correct_name = "MAESTRO(A) ESPECIALISTA DOCENTE DE APOYO"
    
    # Check count before update
    count = Maestro.objects.filter(funcion=target_incorrect).count()
    print(f"Found {count} records with function '{target_incorrect}'")
    
    if count > 0:
        # Perform update
        updated = Maestro.objects.filter(funcion=target_incorrect).update(funcion=correct_name)
        print(f"Updated {updated} records to '{correct_name}'")
    else:
        print(f"No records found with '{target_incorrect}'.")

if __name__ == '__main__':
    update_funciones_v2()
