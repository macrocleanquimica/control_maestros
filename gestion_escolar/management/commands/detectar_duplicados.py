from django.core.management.base import BaseCommand
from django.db.models import Count
from gestion_escolar.models import Maestro
from collections import defaultdict

class Command(BaseCommand):
    help = 'Detecta maestros duplicados basándose en clave_presupuestal, curp, rfc, id_escuela, a_paterno, a_materno, nombres'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Antes de detectar, limpia espacios al inicio/final de los campos de texto en todos los maestros'
        )

    def handle(self, *args, **options):
        if options['limpiar']:
            self._limpiar_espacios()

        self.stdout.write(self.style.SUCCESS('Buscando maestros duplicados...\n'))

        todos = Maestro.objects.select_related('id_escuela').all().order_by('fecha_registro')

        grupos = defaultdict(list)
        for m in todos:
            clave = (
                (m.clave_presupuestal or '').strip(),
                (m.curp or '').strip(),
                (m.rfc or '').strip(),
                str(m.id_escuela_id or ''),
                (m.a_paterno or '').strip(),
                (m.a_materno or '').strip(),
                (m.nombres or '').strip(),
            )
            grupos[clave].append(m)

        grupos_dup = {k: v for k, v in grupos.items() if len(v) > 1}

        if not grupos_dup:
            self.stdout.write(self.style.SUCCESS('No se encontraron maestros duplicados.'))
            return

        self.stdout.write(self.style.WARNING(
            f'Se encontraron {len(grupos_dup)} grupo(s) de maestros duplicados:\n'
        ))

        total_registros = 0
        for clave, registros in sorted(grupos_dup.items()):
            total_registros += len(registros)
            escuela = registros[0].id_escuela
            escuela_str = f"{escuela.nombre_ct} (CCT: {escuela.id_escuela})" if escuela else "SIN ESCUELA"
            r = registros[0]

            self.stdout.write('-' * 60)
            self.stdout.write(f'Clave Presupuestal: {clave[0] or "VACIO"}')
            self.stdout.write(f'CURP: {clave[1] or "VACIO"}')
            self.stdout.write(f'RFC: {clave[2] or "VACIO"}')
            self.stdout.write(f'Escuela: {escuela_str}')
            self.stdout.write(f'Nombre: {clave[4]} {clave[5]} {clave[6]}')
            self.stdout.write(f'Total de registros: {len(registros)}\n')

            for i, m in enumerate(registros, 1):
                self.stdout.write(
                    f'  [{i}] ID: {m.id_maestro} | '
                    f'Status: {m.status} | '
                    f'F.Registro: {m.fecha_registro.strftime("%Y-%m-%d %H:%M")} | '
                    f'F.Act: {m.fecha_actualizacion.strftime("%Y-%m-%d %H:%M")} | '
                    f'Funcion: {m.funcion or "N/A"} | '
                    f'Plaza: {m.num_plaza or "N/A"} | '
                    f'Principal: {m.maestro_principal_id or "N/A"}'
                )

            self.stdout.write('')
            relaciones = self._contar_relaciones(registros)
            if relaciones:
                self.stdout.write(self.style.WARNING('  Relaciones existentes por ID:'))
                for id_m, tabs in sorted(relaciones.items()):
                    partes = [f'    ID {id_m}:']
                    for tabla, cnt in sorted(tabs.items()):
                        if cnt > 0:
                            partes.append(f'{tabla}={cnt}')
                    self.stdout.write(' | '.join(partes))
                self.stdout.write('')

        self.stdout.write('=' * 60)
        self.stdout.write(self.style.WARNING(
            f'RESUMEN: {len(grupos_dup)} grupo(s) con un total de {total_registros} registros duplicados.'
        ))
        self.stdout.write(self.style.SUCCESS(
            '\nSiguiente paso: definir que maestro conservar en cada grupo.\n'
            'Luego ejecutaremos: python manage.py unificar_maestros'
        ))

    def _limpiar_espacios(self):
        self.stdout.write(self.style.WARNING('Limpiando espacios en campos de texto...'))
        campos = ['a_paterno', 'a_materno', 'nombres', 'curp', 'rfc', 'clave_presupuestal']
        contador = 0
        for m in Maestro.objects.all():
            dirty = False
            for campo in campos:
                valor = getattr(m, campo, None)
                if valor and valor != valor.strip():
                    setattr(m, campo, valor.strip())
                    dirty = True
            if dirty:
                m.save(update_fields=campos)
                contador += 1
        self.stdout.write(self.style.SUCCESS(f'Se limpiaron {contador} maestros.\n'))

    def _contar_relaciones(self, registros):
        from gestion_escolar.models import Vacancia
        relaciones = {}
        for m in registros:
            rid = m.id_maestro
            r = {}
            r['Zonas_supervisadas'] = m.zonas_supervisadas.count()
            r['Director'] = 1 if getattr(m, 'director', None) is not None else 0
            r['Vacancias_titular'] = m.vacancia_set.count()
            r['Vacancias_interino'] = Vacancia.objects.filter(maestro_interino=m).count()
            r['Historial'] = m.historial_set.count()
            r['Documentos'] = m.documentos_expediente.count()
            r['Kardex'] = m.kardexmovimiento_set.count()
            r['FUPs'] = m.fups.count()
            r['Correspondencia'] = m.correspondencia_recibida.count()
            r['Plazas_secundarias'] = m.plazas_secundarias.count()
            r['Maestro_principal'] = 1 if m.maestro_principal else 0
            relaciones[rid] = r
        return relaciones
