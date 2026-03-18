from django.core.management.base import BaseCommand
from django.db import transaction
from unidecode import unidecode
from gestion_escolar.models import Maestro
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Normaliza los espacios en los nombres de los maestros existentes y actualiza nombre_completo_unaccented.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando normalización de nombres de maestros...'))
        
        updated_count = 0
        total_maestros = Maestro.objects.count()

        with transaction.atomic():
            for i, maestro in enumerate(Maestro.objects.all()):
                self.stdout.write(f'Procesando maestro {i+1}/{total_maestros}: {maestro.nombres} {maestro.a_paterno}', ending=r'\r')
                
                # Reconstruimos full_name con la lógica de normalización de espacios
                # " ".join(some_string.split()) reduce múltiples espacios a uno solo
                full_name = " ".join(
                    f"{maestro.nombres or ''} {maestro.a_paterno or ''} {maestro.a_materno or ''}"
                    .split()
                ).upper()
                
                new_nombre_completo_unaccented = unidecode(full_name)

                if maestro.nombre_completo_unaccented != new_nombre_completo_unaccented:
                    maestro.nombre_completo_unaccented = new_nombre_completo_unaccented
                    maestro.save(update_fields=['nombre_completo_unaccented'])
                    updated_count += 1
            
            self.stdout.write('\n') # Nueva línea después del contador progresivo

        self.stdout.write(self.style.SUCCESS(
            f'Normalización completada. Se actualizaron {updated_count} de {total_maestros} maestros.'
        ))