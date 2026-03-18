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

def check_especialidad():
    # Fuzzy search for 'CON ESPECIALIDAD'
    funcs = list(Maestro.objects.filter(funcion__icontains='CON ESPECIALIDAD').values('funcion').annotate(count=Count('id_maestro')))
    
    with open('check_especialidad.json', 'w', encoding='utf-8') as f:
        json.dump(funcs, f, indent=4)

if __name__ == '__main__':
    check_especialidad()
