import csv
from django.core.management.base import BaseCommand, CommandError
from gestion_escolar.models import Prelacion

class Command(BaseCommand):
    help = 'Importa datos de prelación desde un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='La ruta al archivo CSV a importar')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']

        try:
            with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                if not all(field in reader.fieldnames for field in ['pos_orden', 'FOLIO', 'CURP', 'NOMBRE', 'tipo_val']):
                    raise CommandError("El archivo CSV debe contener las columnas: pos_orden, FOLIO, CURP, NOMBRE, tipo_val")
                
                imported_count = 0
                updated_count = 0
                errors = []

                for row in reader:
                    try:
                        # Convertir pos_orden a entero
                        pos_orden = int(row['pos_orden'])

                        # Intentar obtener o crear el objeto Prelacion
                        # Usamos 'folio' como identificador único para actualizar o crear
                        prelacion, created = Prelacion.objects.update_or_create(
                            folio=row['FOLIO'],
                            defaults={
                                'pos_orden': pos_orden,
                                'curp': row['CURP'],
                                'nombre': row['NOMBRE'],
                                'tipo_val': row['tipo_val'],
                            }
                        )
                        if created:
                            imported_count += 1
                        else:
                            updated_count += 1
                    except ValueError as e:
                        errors.append(f"Error de valor en la fila {reader.line_num}: {e} - Datos: {row}")
                    except Exception as e:
                        errors.append(f"Error al procesar la fila {reader.line_num}: {e} - Datos: {row}")

            self.stdout.write(self.style.SUCCESS(f'Importación finalizada.'))
            self.stdout.write(self.style.SUCCESS(f'Registros creados: {imported_count}'))
            self.stdout.write(self.style.SUCCESS(f'Registros actualizados: {updated_count}'))
            
            if errors:
                self.stdout.write(self.style.WARNING('Se encontraron errores durante la importación:'))
                for error in errors:
                    self.stdout.write(self.style.ERROR(f'- {error}'))

        except FileNotFoundError:
            raise CommandError(f'El archivo CSV "{csv_file_path}" no fue encontrado')
        except Exception as e:
            raise CommandError(f'Ocurrió un error inesperado: {e}')