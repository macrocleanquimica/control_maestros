
import sqlite3
import csv
import os

# Define la ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Nombres de los archivos de base de datos y CSV
db_filename = 'db_current_RESP.sqlite3'
csv_filename = 'historial_recuperado.csv'
db_path = os.path.join(BASE_DIR, db_filename)
csv_path = os.path.join(BASE_DIR, csv_filename)

# Nombre de la tabla en la base de datos
table_name = 'gestion_escolar_historial'

print(f"Iniciando exportación desde '{db_filename}' a '{csv_filename}'...")

try:
    # Conectar a la base de datos SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Obtener los nombres de las columnas
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]

    # Obtener todos los datos de la tabla
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()

    # Escribir los datos a un archivo CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        
        # Escribir la fila de encabezado
        csv_writer.writerow(columns)
        
        # Escribir las filas de datos
        csv_writer.writerows(rows)

    print(f"¡Éxito! Se han exportado {len(rows)} filas a '{csv_filename}'.")

except sqlite3.Error as e:
    print(f"Error de base de datos: {e}")
except Exception as e:
    print(f"Ocurrió un error inesperado: {e}")

finally:
    if 'conn' in locals() and conn:
        conn.close()
