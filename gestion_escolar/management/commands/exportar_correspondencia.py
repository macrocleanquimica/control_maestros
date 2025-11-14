
import csv
import sqlite3
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Exporta datos de la tabla de correspondencia desde un archivo de base de datos SQLite de respaldo a un archivo CSV.'

    def handle(self, *args, **options):
        db_file = 'db_current_RESP.sqlite3'
        table_name = 'gestion_escolar_registrocorrespondencia'
        output_csv_file = 'correspondencia_recuperada.csv'

        self.stdout.write(f"Iniciando exportación desde '{db_file}' a '{output_csv_file}'...")

        try:
            # Conectar directamente al archivo de respaldo de SQLite
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            # Verificar si la tabla existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
            if cursor.fetchone() is None:
                raise CommandError(f"La tabla '{table_name}' no se encontró en la base de datos '{db_file}'.")

            # Extraer datos y encabezados
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            column_names = [description[0] for description in cursor.description]

            # Escribir al archivo CSV
            with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(column_names)
                csv_writer.writerows(rows)

            self.stdout.write(self.style.SUCCESS(f"¡Éxito! Se han exportado {len(rows)} filas a '{output_csv_file}'."))

        except sqlite3.Error as e:
            raise CommandError(f"Error de base de datos al procesar '{db_file}': {e}")
        except Exception as e:
            raise CommandError(f"Ocurrió un error inesperado: {e}")
        finally:
            if 'conn' in locals() and conn:
                conn.close()
