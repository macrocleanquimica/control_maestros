import os
import django
import csv

# Configura el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Categoria

def importar_categorias(csv_filepath):
    """
    Importa categorías desde un archivo CSV a la base de datos.
    El CSV debe tener las columnas: ID_Categoria, Descripcion
    """
    print(f"Iniciando importación desde {csv_filepath}...")
    
    try:
        with open(csv_filepath, mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.reader(csv_file)
            
            # Omitir la fila de encabezado
            next(csv_reader)
            
            for row in csv_reader:
                if not row:  # Omitir filas vacías
                    continue
                
                id_cat = row[0].strip()
                desc = row[1].strip()
                
                if not id_cat: # Omitir filas sin ID
                    print("Advertencia: Se encontró una fila sin ID_Categoria. Se omitirá.")
                    continue

                # Usar get_or_create para evitar duplicados
                obj, created = Categoria.objects.get_or_create(
                    id_categoria=id_cat,
                    defaults={'descripcion': desc}
                )
                
                if created:
                    print(f"Categoría creada: {obj.id_categoria} - {obj.descripcion}")
                else:
                    # Si ya existe, verifica si la descripción necesita actualizarse
                    if obj.descripcion != desc:
                        print(f"Categoría '{id_cat}' ya existe. Actualizando descripción...")
                        obj.descripcion = desc
                        obj.save()
                    else:
                        print(f"Categoría '{id_cat}' ya existe. No se requieren cambios.")

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {csv_filepath}. Asegúrate de que el nombre y la ubicación son correctos.")
        return
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
        return

    print("\nImportación de categorías finalizada.")

if __name__ == '__main__':
    # El nombre del archivo CSV que el usuario confirmó
    csv_file_name = 'categorias_plantilla.csv'
    importar_categorias(csv_file_name)
