import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Maestro
from django.db.models import Count

def check_fua_consistency():
    target_function = "MAESTRO(A) ESPECIALISTA DOCENTE DE APOYO"
    expected_cct_prefix = "10FUA"
    
    # Find records with the specific function that do NOT start with the expected prefix
    mismatches = Maestro.objects.filter(funcion=target_function).exclude(id_escuela__id_escuela__startswith=expected_cct_prefix)
    
    count = mismatches.count()
    total = Maestro.objects.filter(funcion=target_function).count()
    
    print(f"Total records with function '{target_function}': {total}")
    print(f"Records NOT in '{expected_cct_prefix}': {count}")
    
    if count > 0:
        print("\nMismatched Records Summary (by CCT Prefix):")
        # Group by first 5 chars of CCT to see patterns
        prefixes = {}
        for m in mismatches:
            cct = m.id_escuela.id_escuela if m.id_escuela else "NO_ESCUELA"
            prefix = cct[:5]
            if prefix not in prefixes:
                prefixes[prefix] = 0
            prefixes[prefix] += 1
            
        for prefix, cnt in prefixes.items():
            print(f"Prefix: {prefix}... | Count: {cnt}")
            
        print("\nDetail of first 20 mismatches:")
        for m in mismatches[:20]:
            print(f"ID: {m.id_maestro} | CCT: {m.id_escuela.id_escuela if m.id_escuela else 'None'} | Name: {m}")

if __name__ == '__main__':
    check_fua_consistency()
