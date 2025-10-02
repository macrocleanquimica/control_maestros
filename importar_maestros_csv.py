import csv
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Maestro, Escuela

CSV_PATH = 'maestros_ejemplo.csv'  # Cambia el nombre si tu archivo es diferente

with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        try:
            escuela = Escuela.objects.get(id_escuela=row['id_escuela'])
            maestro, creado = Maestro.objects.get_or_create(
                id_maestro=row['id_maestro'],
                defaults={
                    'a_paterno': row['a_paterno'],
                    'a_materno': row['a_materno'],
                    'nombres': row['nombres'],
                    'curp': row['curp'],
                    'rfc': row['rfc'],
                    'sexo': row['sexo'],
                    'est_civil': row['est_civil'],
                    'fecha_nacimiento': row['fecha_nacimiento'] or None,
                    'id_escuela': escuela,
                    'techo_f': row['techo_f'],
                    'dep': row['dep'],
                    'unid': row['unid'],
                    'sub_unid': row['sub_unid'],
                    'categog': row['categog'],
                    'hrs': row['hrs'],
                    'num_plaza': row['num_plaza'],
                    'codigo': row['codigo'],
                    'fecha_ingreso': row['fecha_ingreso'] or None,
                    'fecha_promocion': row['fecha_promocion'] or None,
                    'form_academica': row['form_academica'],
                    'horario': row['horario'],
                    'funcion': row['funcion'],
                    'nivel_estudio': row['nivel_estudio'],
                    'domicilio_part': row['domicilio_part'],
                    'poblacion': row['poblacion'],
                    'codigo_postal': row['codigo_postal'],
                    'telefono': row['telefono'],
                    'email': row['email'],
                    'status': row['status'],
                    'observaciones': row['observaciones']
                }
            )
            if not creado:
                # Actualizar los campos si ya existe
                maestro.a_paterno = row['a_paterno']
                maestro.a_materno = row['a_materno']
                maestro.nombres = row['nombres']
                maestro.curp = row['curp']
                maestro.rfc = row['rfc']
                maestro.sexo = row['sexo']
                maestro.est_civil = row['est_civil']
                maestro.fecha_nacimiento = row['fecha_nacimiento'] or None
                maestro.id_escuela = escuela
                maestro.techo_f = row['techo_f']
                maestro.dep = row['dep']
                maestro.unid = row['unid']
                maestro.sub_unid = row['sub_unid']
                maestro.categog = row['categog']
                maestro.hrs = row['hrs']
                maestro.num_plaza = row['num_plaza']
                maestro.codigo = row['codigo']
                maestro.fecha_ingreso = row['fecha_ingreso'] or None
                maestro.fecha_promocion = row['fecha_promocion'] or None
                maestro.form_academica = row['form_academica']
                maestro.horario = row['horario']
                maestro.funcion = row['funcion']
                maestro.nivel_estudio = row['nivel_estudio']
                maestro.domicilio_part = row['domicilio_part']
                maestro.poblacion = row['poblacion']
                maestro.codigo_postal = row['codigo_postal']
                maestro.telefono = row['telefono']
                maestro.email = row['email']
                maestro.status = row['status']
                maestro.observaciones = row['observaciones']
                maestro.full_clean()
                maestro.save()
                print(f"Maestro '{maestro.nombres}' actualizado correctamente.")
            else:
                maestro.full_clean()
                maestro.save()
                print(f"Maestro '{maestro.nombres}' creado correctamente.")
        except Exception as e:
            print(f"Error con el maestro {row['nombres']}: {e}")
