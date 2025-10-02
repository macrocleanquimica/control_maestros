import csv
import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Maestro, Escuela

CSV_PATH = 'maestros_migracion.csv'  # Cambia el nombre si tu archivo es diferente

def convertir_fecha(fecha_str):
    if not fecha_str or fecha_str.strip() == '':
        return None
    for fmt in ('%d-%b-%y', '%d-%b-%Y', '%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(fecha_str.strip(), fmt).date()
        except Exception:
            continue
    return None

with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        try:
            id_escuela = row.get('ID_Escuelas') or row.get('ID_Escuela') or row.get('id_escuela')
            if not id_escuela:
                print(f"Error: No se encontró columna de escuela para el maestro {row.get('Nombres','')}.")
                continue
            try:
                escuela = Escuela.objects.get(id_escuela=id_escuela)
            except Escuela.DoesNotExist:
                print(f"Error: Escuela '{id_escuela}' no encontrada para el maestro {row.get('Nombres','')}.")
                continue
            id_maestro = str(row['ID_Maestro']).zfill(5)
            num_plaza = str(row['Num_Plaza']) if row['Num_Plaza'] else ''
            nivel_estudio = row['Nivel_Estudio'] if row['Nivel_Estudio'].strip() else 'Prof.'
            maestro, creado = Maestro.objects.get_or_create(
                id_maestro=id_maestro,
                defaults={
                    'a_paterno': row['A_Paterno'],
                    'a_materno': row['A_Materno'],
                    'nombres': row['Nombres'],
                    'curp': row['Curp'],
                    'rfc': row['RFC'],
                    'sexo': row['Sexo'],
                    'dep': row['DEP'],
                    'unid': row['UNID'],
                    'sub_unid': row['SUB_UNID'],
                    'categog': row['CATEG'],
                    'hrs': row['HRS'],
                    'num_plaza': num_plaza,
                    'codigo': row['Codigo'],
                    'fecha_ingreso': convertir_fecha(row['Fecha_Ingreso']),
                    'fecha_promocion': convertir_fecha(row['Fecha_Promocion']),
                    'form_academica': row['Form_Academica'],
                    'horario': row['Horario'],
                    'funcion': row['Funcion'],
                    'est_civil': row['Est_Civil'],
                    'domicilio_part': row['Domicilio_Part'],
                    'poblacion': row['Poblacion'],
                    'codigo_postal': row['Codigo_Postal'],
                    'telefono': row['Tel'],
                    'email': row['Email'],
                    'status': row['Status'],
                    'observaciones': row['Observaciones'],
                    'nivel_estudio': nivel_estudio,
                    'id_escuela': escuela
                }
            )
            if not creado:
                maestro.a_paterno = row['A_Paterno']
                maestro.a_materno = row['A_Materno']
                maestro.nombres = row['Nombres']
                maestro.curp = row['Curp']
                maestro.rfc = row['RFC']
                maestro.sexo = row['Sexo']
                maestro.dep = row['DEP']
                maestro.unid = row['UNID']
                maestro.sub_unid = row['SUB_UNID']
                maestro.categog = row['CATEG']
                maestro.hrs = row['HRS']
                maestro.num_plaza = num_plaza
                maestro.codigo = row['Codigo']
                maestro.fecha_ingreso = convertir_fecha(row['Fecha_Ingreso'])
                maestro.fecha_promocion = convertir_fecha(row['Fecha_Promocion'])
                maestro.form_academica = row['Form_Academica']
                maestro.horario = row['Horario']
                maestro.funcion = row['Funcion']
                maestro.est_civil = row['Est_Civil']
                maestro.domicilio_part = row['Domicilio_Part']
                maestro.poblacion = row['Poblacion']
                maestro.codigo_postal = row['Codigo_Postal']
                maestro.telefono = row['Tel']
                maestro.email = row['Email']
                maestro.status = row['Status']
                maestro.observaciones = row['Observaciones']
                maestro.nivel_estudio = nivel_estudio
                maestro.id_escuela = escuela
                maestro.full_clean()
                maestro.save()
                print(f"Maestro '{maestro.nombres}' actualizado correctamente.")
            else:
                maestro.full_clean()
                maestro.save()
                print(f"Maestro '{maestro.nombres}' creado correctamente.")
        except Exception as e:
            print(f"Error con el maestro {row.get('Nombres','')}: {e}")
