import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Maestro
from django.db.models import Count

def check_funciones_final():
    # Find all distinct functions containing 'APOYO'
    funciones = Maestro.objects.filter(funcion__icontains='APOYO').values('funcion').annotate(count=Count('id_maestro')).order_by('funcion')
    
    with open('funciones_output.txt', 'w', encoding='utf-8') as f:
        f.write("-" * 50 + "\n")
        for reg in funciones:
            f.write(f"FUNC: {reg['funcion']} | COUNT: {reg['count']}\n")
        f.write("-" * 50 + "\n")

if __name__ == '__main__':
    check_funciones_final()
