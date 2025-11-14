
import sqlite3
import csv
import sys

# Basado en la estructura de Django, el nombre de la tabla probablemente sea este.
# Si el script falla, podríamos tener que ajustar este nombre.
NOMBRE_TABLA = 'gestion_escolar_registrocorrespondencia'
DB_FILE = 'db_current_RESP.sqlite3'
OUTPUT_CSV_FILE = 'correspondencia_recuperada.csv'

def exportar_tabla_a_csv():
    """
    Conecta a una base de datos SQLite, lee todos los datos de una tabla
    y los exporta a un archivo CSV.
    """
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Obtener los datos de la tabla
        cursor.execute(f"SELECT * FROM {NOMBRE_TABLA}")
        rows = cursor.fetchall()

        # Obtener los nombres de las columnas
        column_names = [description[0] for description in cursor.description]

        # Escribir los datos a un archivo CSV
        with open(OUTPUT_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            # Escribir la fila de encabezado
            csv_writer.writerow(column_names)
            # Escribir las filas de datos
            csv_writer.writerows(rows)

        print(f"¡Éxito! Se han exportado {len(rows)} filas de la tabla '{NOMBRE_TABLA}' a '{OUTPUT_CSV_FILE}'")

    except sqlite3.Error as e:
        print(f"Error de base de datos: {e}", file=sys.stderr)
        print(f"Asegúrate de que el archivo '{DB_FILE}' existe y no está corrupto.", file=sys.stderr)
        print(f"También, verifica si la tabla '{NOMBRE_TABLA}' es correcta.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Cerrar la conexión
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    exportar_tabla_a_csv()
