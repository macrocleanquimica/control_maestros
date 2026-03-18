import os
import django
import sys
import json

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Maestro
from django.db.models import Count

def check_funciones():
    # Find all distinct functions containing 'APOYO'
    funciones = list(Maestro.objects.filter(funcion__icontains='APOYO').values('funcion').annotate(count=Count('id_maestro')).order_by('funcion'))
    print(json.dumps(funciones, indent=4))

if __name__ == '__main__':
    check_funciones()
