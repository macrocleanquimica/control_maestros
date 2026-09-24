"""
Comando para importar el directorio de escuelas regulares desde un CSV.

Uso:
    python manage.py importar_directorio_escuelas ruta/al/archivo.csv
    python manage.py importar_directorio_escuelas ruta/al/archivo.csv --borrar

El CSV debe tener las columnas:
ZONA, CLAVE E.E., CCT, NOMBRE DE LA ESCUELA, NIVEL, TIPO, CALLE Y NUM,
COLONIA, CP, LOCALIDAD, MUNICIPIO, TURNO, SUPERVISOR,
NOMBRE DEL DIRECTOR DE LA ESCUELA, NOMBRE MAESTRO DE APOYO, SEGUNDO MAESTRO APOYO
"""

from django.core.management.base import BaseCommand, CommandError
from gestion_escolar.models import EscuelaRegular, Escuela
import csv
import os


class Command(BaseCommand):
    help = 'Importa el directorio de escuelas regulares desde un CSV'

    def add_arguments(self, parser):
        parser.add_argument('archivo_csv', type=str, help='Ruta al archivo CSV')
        parser.add_argument(
            '--borrar',
            action='store_true',
            help='Borrar registros existentes antes de importar',
        )

    def handle(self, *args, **options):
        archivo_path = options['archivo_csv']

        if not os.path.exists(archivo_path):
            raise CommandError(f'El archivo "{archivo_path}" no existe')

        self.stdout.write(self.style.SUCCESS(f'Leyendo archivo: {archivo_path}'))

        if options['borrar']:
            count = EscuelaRegular.objects.count()
            EscuelaRegular.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Se eliminaron {count} registros existentes.'))

        creados = 0
        actualizados = 0
        omitidos_cct = 0
        omitidos_vacios = 0
        errores = []

        try:
            with open(archivo_path, 'r', encoding='latin-1') as f:
                reader = csv.DictReader(f)

                for i, row in enumerate(reader, start=2):
                    cct_col = row.get('CCT', '').strip()
                    clave_ee_col = row.get('CLAVE E.E.', '').strip()
                    nombre_escuela = row.get('NOMBRE DE LA ESCUELA', '').strip()

                    # Determinar el CCT FUA: puede estar en la columna CCT o en CLAVE E.E.
                    if 'FUA' in cct_col.upper():
                        cct_codigo = cct_col
                    elif 'FUA' in clave_ee_col.upper():
                        cct_codigo = clave_ee_col
                    # El formato "U.S.A.E.R No. NN" mapea al CCT FUA correspondiente
                    elif clave_ee_col.upper().startswith('U.S.A.E.R'):
                        cct_codigo = self._resolver_usaer(clave_ee_col, archivo_path, row)
                    else:
                        cct_codigo = cct_col

                    if not cct_codigo or not nombre_escuela:
                        omitidos_vacios += 1
                        continue

                    # Buscar el CCT en la base de datos
                    try:
                        escuela_cct = Escuela.objects.get(id_escuela=cct_codigo)
                    except Escuela.DoesNotExist:
                        omitidos_cct += 1
                        errores.append(f'Linea {i}: CCT "{cct_codigo}" no encontrado en BD')
                        continue

                    nivel = row.get('NIVEL', '').strip().upper()
                    subsistema = row.get('TIPO', '').strip().upper()
                    turno = row.get('TURNO', '').strip().upper()

                    # Normalizar turnos
                    turno_map = {'M': 'MATUTINO', 'V': 'VESPERTINO'}
                    if turno in turno_map:
                        turno = turno_map[turno]

                    data = {
                        'cct': escuela_cct,
                        'nombre_escuela': nombre_escuela[:200],
                        'nivel': nivel[:20] if nivel else '',
                        'subsistema': subsistema[:20] if subsistema else '',
                        'calle_num': next((row[k] for k in row if k.startswith('CALLE Y N') and k.endswith('M')), '').strip()[:250],
                        'colonia': row.get('COLONIA', '').strip()[:150],
                        'cp': row.get('CP', '').strip()[:10],
                        'localidad': row.get('LOCALIDAD', '').strip()[:150],
                        'municipio': row.get('MUNICIPIO', '').strip()[:150],
                        'turno': turno[:30] if turno else '',
                        'supervisor': row.get('SUPERVISOR', '').strip()[:200],
                        'director': row.get('NOMBRE DEL DIRECTOR DE LA ESCUELA', '').strip()[:200],
                        'maestro_apoyo': row.get('NOMBRE MAESTRO DE APOYO', '').strip()[:200],
                        'segundo_maestro_apoyo': row.get('SEGUNDO MAESTRO APOYO', '').strip()[:200],
                    }

                    # Verificar si ya existe (por CCT + nombre de escuela)
                    existing = EscuelaRegular.objects.filter(
                        cct=escuela_cct,
                        nombre_escuela=nombre_escuela
                    ).first()

                    if existing:
                        for key, value in data.items():
                            setattr(existing, key, value)
                        existing.save()
                        actualizados += 1
                    else:
                        EscuelaRegular.objects.create(**data)
                        creados += 1

        except Exception as e:
            raise CommandError(f'Error al procesar el archivo: {str(e)}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Resumen de Importación ==='))
        self.stdout.write(self.style.SUCCESS(f'  Creados: {creados}'))
        self.stdout.write(self.style.SUCCESS(f'  Actualizados: {actualizados}'))
        self.stdout.write(self.style.WARNING(f'  Omitidos (CCT no encontrado): {omitidos_cct}'))
        self.stdout.write(self.style.WARNING(f'  Omitidos (datos vacíos): {omitidos_vacios}'))

        if errores:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'Errores ({len(errores)}):'))
            for err in errores[:20]:
                self.stdout.write(self.style.ERROR(f'  {err}'))
            if len(errores) > 20:
                self.stdout.write(self.style.ERROR(f'  ... y {len(errores) - 20} errores más'))

        total = creados + actualizados
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Total procesados: {total} escuelas regulares'))

    def _resolver_usaer(self, clave_ee, archivo_path, fila_actual):
        """Resuelve el CCT FUA a partir de la etiqueta 'U.S.A.E.R. No. NN'.

        El número NN se mapea al CCT FUA con prefijo '10FUA00{NN}' que
        exista en la base de datos (la letra de verificación varía).
        """
        import re
        m = re.search(r'U\.S\.A\.E\.R\.?\s*No\.?\s*(\d+)', clave_ee, re.IGNORECASE)
        if not m:
            return ''
        numero = m.group(1)
        prefijo = f'10FUA{int(numero):04d}'

        escuela = Escuela.objects.filter(id_escuela__startswith=prefijo).first()
        return escuela.id_escuela if escuela else ''
