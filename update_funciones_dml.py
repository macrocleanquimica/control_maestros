import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Maestro

def update_funciones_dml():
    # Criteria
    target_cct_prefix = "10DML"
    target_function = "MAESTRO(A) ESPECIALISTA DOCENTE DE APOYO"
    new_function = "MAESTRO (A) DOCENTE ESPECIALISTA"
    
    # Filter query
    maestros_to_update = Maestro.objects.filter(
        id_escuela__id_escuela__startswith=target_cct_prefix,
        funcion=target_function
    )
    
    count = maestros_to_update.count()
    print(f"Found {count} maestros in '{target_cct_prefix}' schools with function '{target_function}'")
    
    if count > 0:
        updated = maestros_to_update.update(funcion=new_function)
        print(f"Successfully updated {updated} records to '{new_function}'")

if __name__ == '__main__':
    update_funciones_dml()
