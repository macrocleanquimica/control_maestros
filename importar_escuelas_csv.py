import csv
import os
import django

# Configura el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Escuela, Zona

CSV_PATH = 'escuelas_ejemplo.csv'  # Cambia el nombre si tu archivo es diferente

def obtener_csv_reader(path):
    """Intenta abrir el archivo CSV en utf-8 y si falla, en latin-1, devolviendo el reader y el archivo abierto."""
    try:
        csvfile = open(path, newline='', encoding='utf-8')
        return csv.DictReader(csvfile), csvfile
    except UnicodeDecodeError:
        print("Advertencia: El archivo no está en UTF-8. Intentando con latin-1...")
        csvfile = open(path, newline='', encoding='latin-1')
        return csv.DictReader(csvfile), csvfile

reader, csvfile = obtener_csv_reader(CSV_PATH)
with csvfile:
    for row in reader:
        try:
            zona = Zona.objects.get(numero=row['zona_esc'])
            escuela, creado = Escuela.objects.get_or_create(
                id_escuela=row['id_escuela'],
                defaults={
                    'nombre_ct': row['nombre_ct'],
                    'zona_esc': zona,
                    'turno': row['turno'],
                    'domicilio': row['domicilio'],
                    'telefono_ct': row['telefono_ct'],
                    'zona_economica': row['zona_economica'],
                    'region': row['region'],
                    'u_d': row['u_d'],
                    'sostenimiento': row['sostenimiento']
                }
            )
            if not creado:
                # Actualizar los campos si ya existe
                escuela.nombre_ct = row['nombre_ct']
                escuela.zona_esc = zona
                escuela.turno = row['turno']
                escuela.domicilio = row['domicilio']
                escuela.telefono_ct = row['telefono_ct']
                escuela.zona_economica = row['zona_economica']
                escuela.region = row['region']
                escuela.u_d = row['u_d']
                escuela.sostenimiento = row['sostenimiento']
                escuela.full_clean()
                escuela.save()
                print(f"Escuela '{escuela.nombre_ct}' actualizada correctamente.")
            else:
                escuela.full_clean()
                escuela.save()
                print(f"Escuela '{escuela.nombre_ct}' creada correctamente.")
        except Exception as e:
            print(f"Error con la escuela {row['nombre_ct']}: {e}")
