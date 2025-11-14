import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from gestion_escolar.models import RegistroCorrespondencia
from datetime import datetime

class Command(BaseCommand):
    help = 'Importa datos de correspondencia desde un archivo CSV a la base de datos activa.'

    def handle(self, *args, **options):
        csv_file_path = 'correspondencia_recuperada.csv'
        self.stdout.write(f"Iniciando importación desde '{csv_file_path}'...")

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                with transaction.atomic():
                    registros_creados = 0
                    for i, row in enumerate(reader, start=2): # Empezar en 2 para el número de fila
                        fecha_recibido_str = row.get('fecha_recibido')
                        fecha_oficio_str = row.get('fecha_oficio')
                        self.stdout.write(f"Fila {i}: fecha_recibido_str='{fecha_recibido_str}'")

                        # Validar y convertir fechas
                        fecha_recibido = None
                        if fecha_recibido_str:
                            try:
                                fecha_recibido = datetime.strptime(fecha_recibido_str, '%Y-%m-%d').date()
                            except ValueError:
                                self.stderr.write(f"Advertencia: Formato de fecha inválido para fecha_recibido '{fecha_recibido_str}' en la fila {i}. Se saltará el registro.")
                                continue

                        fecha_oficio = None
                        if fecha_oficio_str:
                            try:
                                fecha_oficio = datetime.strptime(fecha_oficio_str, '%Y-%m-%d').date()
                            except ValueError:
                                self.stderr.write(f"Advertencia: Formato de fecha inválido para fecha_oficio '{fecha_oficio_str}' en la fila {i}. Se saltará el registro.")
                                continue
                        
                        if not fecha_recibido:
                            self.stderr.write(f"Error en la fila {i}: 'fecha_recibido' no puede ser nula. Saltando registro.")
                            continue
                        
                        if not fecha_oficio:
                            self.stderr.write(f"Error en la fila {i}: 'fecha_oficio' no puede ser nula. Saltando registro.")
                            continue

                        RegistroCorrespondencia.objects.create(
                            folio_documento=row.get('folio_documento'),
                            fecha_recibido=fecha_recibido,
                            contenido=row.get('contenido'),
                            remitente=row.get('remitente'),
                            area=row.get('area'),
                            observaciones=row.get('observaciones'),
                            fecha_oficio=fecha_oficio,
                            tipo_documento=row.get('tipo_documento'),
                            quien_recibio=row.get('quien_recibio')
                        )
                        registros_creados += 1

            self.stdout.write(self.style.SUCCESS(f"¡Éxito! Se han importado {registros_creados} registros de correspondencia."))

        except FileNotFoundError:
            raise CommandError(f"Error: No se encontró el archivo '{csv_file_path}'. Asegúrate de que está en el directorio correcto.")
        except Exception as e:
            raise CommandError(f"Ocurrió un error inesperado durante la importación: {e}")