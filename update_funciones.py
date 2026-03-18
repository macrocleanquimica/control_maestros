import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Maestro

def update_funciones():
    # Incorrect function name (with space inside parenthesis or around it)
    incorrect_name = "MAESTRO (A) DE APOYO"
    correct_name = "MAESTRO(A) DE APOYO"
    
    # Check count before update
    count = Maestro.objects.filter(funcion=incorrect_name).count()
    print(f"Found {count} records with function '{incorrect_name}'")
    
    if count > 0:
        # Perform update
        updated = Maestro.objects.filter(funcion=incorrect_name).update(funcion=correct_name)
        print(f"Updated {updated} records to '{correct_name}'")
    else:
        print("No records found to update. Checking for other variations...")
        # Check if maybe the user meant a variation with different spacing
        variations = Maestro.objects.filter(funcion__icontains="MAESTRO (A) DE APOYO")
        for m in variations:
            print(f"Found variation: '{m.funcion}'")

if __name__ == '__main__':
    update_funciones()
