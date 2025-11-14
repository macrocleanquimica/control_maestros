from django.core.management.base import BaseCommand
from gestion_escolar.models import Maestro
from django.db.models import Value
from django.db.models.functions import Replace

class Command(BaseCommand):
    help = 'Actualiza el campo funcion de "SUPERVISOR (A)" a "SUPERVISOR(A)" en el modelo Maestro'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando actualización de funciones de supervisor...'))
        
        # Busca todas las variaciones de "SUPERVISOR (A)" (ignorando mayúsculas/minúsculas) y con espacio
        maestros_a_actualizar = Maestro.objects.filter(funcion__iregex=r'SUPERVISOR\s*\(A\)')

        if not maestros_a_actualizar.exists():
            self.stdout.write(self.style.WARNING('No se encontraron registros para actualizar.'))
            return

        # Actualiza los registros reemplazando el espacio
        updated_count = maestros_a_actualizar.update(funcion=Replace('funcion', Value(' (A)'), Value('(A)')))

        self.stdout.write(self.style.SUCCESS(f'Se actualizaron {updated_count} registros.'))
        
        # Adicionalmente, se asegura que todos los valores queden en mayúsculas
        final_count = Maestro.objects.filter(funcion__iexact='SUPERVISOR(A)').update(funcion='SUPERVISOR(A)')
        
        self.stdout.write(self.style.SUCCESS(f'Se normalizaron a mayúsculas {final_count} registros.'))
        self.stdout.write(self.style.SUCCESS('Actualización completada.'))
