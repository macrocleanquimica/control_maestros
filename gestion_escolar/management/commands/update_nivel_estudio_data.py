from django.core.management.base import BaseCommand
from gestion_escolar.models import Maestro

class Command(BaseCommand):
    help = 'Actualiza los valores del campo nivel_estudio en el modelo Maestro a mayúsculas y reemplaza "Otro" por "C.".'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando actualización de nivel_estudio...'))
        
        updated_count = 0
        for maestro in Maestro.objects.all():
            original_nivel_estudio = maestro.nivel_estudio
            
            if original_nivel_estudio:
                # Convertir a mayúsculas
                new_nivel_estudio = original_nivel_estudio.upper()
                
                # Reemplazar "OTRO" por "C."
                if new_nivel_estudio == "OTRO":
                    new_nivel_estudio = "C."
                
                if new_nivel_estudio != original_nivel_estudio:
                    maestro.nivel_estudio = new_nivel_estudio
                    maestro.save()
                    updated_count += 1
                    self.stdout.write(f'Actualizado Maestro {maestro.id_maestro}: "{original_nivel_estudio}" -> "{new_nivel_estudio}"')
            
        self.stdout.write(self.style.SUCCESS(f'Actualización completada. Se actualizaron {updated_count} registros.'))
