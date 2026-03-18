import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Maestro

def update_funciones_v3():
    correct_name = "MAESTRO(A) ESPECIALISTA DOCENTE DE APOYO"
    
    # List of incorrect variations to target
    targets = [
        "MAESTRO (A) ESPECIALISTA DOCENTE DE APOYO", # Extra space
        "MTRA ESPECIALISTA DOCENTE DE APOYO",        # MTRA without dot
        "MTRA. ESPECIALISTA DOCENTE DE APOYO"        # MTRA with dot (seen in logs)
    ]
    
    total_updated = 0
    
    print(f"Targeting correct name: '{correct_name}'")
    
    for incorrect_name in targets:
        count = Maestro.objects.filter(funcion=incorrect_name).count()
        if count > 0:
            updated = Maestro.objects.filter(funcion=incorrect_name).update(funcion=correct_name)
            print(f"Updated {updated} records from '{incorrect_name}'")
            total_updated += updated
        else:
            print(f"No records found for '{incorrect_name}'")
            
    print(f"Total records updated: {total_updated}")

if __name__ == '__main__':
    update_funciones_v3()
