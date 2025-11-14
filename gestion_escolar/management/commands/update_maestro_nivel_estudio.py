from django.core.management.base import BaseCommand
from gestion_escolar.models import Maestro

class Command(BaseCommand):
    help = 'Actualiza todos los valores de nivel_estudio de los Maestros a mayúsculas.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando actualización de niveles de estudio...'))
        updated_count = 0
        for maestro in Maestro.objects.all():
            if maestro.nivel_estudio and maestro.nivel_estudio != maestro.nivel_estudio.upper():
                maestro.nivel_estudio = maestro.nivel_estudio.upper()
                maestro.save()
                updated_count += 1
        self.stdout.write(self.style.SUCCESS(f'Se actualizaron {updated_count} registros de nivel de estudio a mayúsculas.'))
