from django.core.management.base import BaseCommand
from django.db import transaction
from gestion_escolar.models import Maestro, Vacancia, Historial, DocumentoExpediente, KardexMovimiento, FUP, RegistroCorrespondencia, Zona
from collections import defaultdict

class Command(BaseCommand):
    help = 'Unifica maestros duplicados: conserva el mas antiguo, re-apunta relaciones, hereda escuela/techo del mas actual, y elimina duplicados'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Buscando grupos de maestros duplicados...\n'))

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
            self.stdout.write(self.style.SUCCESS('No se encontraron maestros duplicados. Nada que hacer.'))
            return

        self.stdout.write(self.style.WARNING(f'Se encontraron {len(grupos_dup)} grupo(s) de duplicados.\n'))

        total_eliminados = 0
        total_reapuntes = 0

        with transaction.atomic():
            for clave, registros in grupos_dup.items():
                registros.sort(key=lambda m: m.fecha_registro)
                conservar = registros[0]
                eliminar = registros[1:]
                mas_actual = registros[-1]

                self.stdout.write(f'--- {conservar.a_paterno} {conservar.a_materno} {conservar.nombres} ---')
                self.stdout.write(f'  Conservar: ID {conservar.id_maestro} (fecha: {conservar.fecha_registro.strftime("%Y-%m-%d")})')
                for e in eliminar:
                    self.stdout.write(f'  Eliminar:  ID {e.id_maestro} (fecha: {e.fecha_registro.strftime("%Y-%m-%d")})')

                for e in eliminar:
                    reapuntes = self._reapuntar_relaciones(conservar, e)
                    total_reapuntes += reapuntes
                    e.delete()
                    total_eliminados += 1

                if len(eliminar) > 0 and mas_actual is not conservar:
                    cambios = []
                    if mas_actual.id_escuela and mas_actual.id_escuela != conservar.id_escuela:
                        conservar.id_escuela = mas_actual.id_escuela
                        cambios.append(f'escuela -> {mas_actual.id_escuela}')
                    if mas_actual.techo_f and mas_actual.techo_f != conservar.techo_f:
                        conservar.techo_f = mas_actual.techo_f
                        cambios.append(f'techo_f -> {mas_actual.techo_f}')
                    if cambios:
                        conservar.save(update_fields=['id_escuela', 'techo_f'])
                        self.stdout.write(f'  Actualizado: {", ".join(cambios)}')

                self.stdout.write('')

        self.stdout.write(self.style.SUCCESS(
            f'Unificacion completada. Se eliminaron {total_eliminados} registro(s) duplicados '
            f'y se re-apuntaron {total_reapuntes} relacion(es).'
        ))

    def _reapuntar_relaciones(self, conservar, eliminar):
        count = 0

        count += self._reapuntar_fk(Zona.objects.filter(supervisor=eliminar), 'supervisor', conservar)
        count += self._reapuntar_fk(Vacancia.objects.filter(maestro_titular=eliminar), 'maestro_titular', conservar)
        count += self._reapuntar_fk(Vacancia.objects.filter(maestro_interino=eliminar), 'maestro_interino', conservar)
        count += self._reapuntar_fk(Historial.objects.filter(maestro=eliminar), 'maestro', conservar)
        count += self._reapuntar_fk(DocumentoExpediente.objects.filter(maestro=eliminar), 'maestro', conservar)
        count += self._reapuntar_fk(KardexMovimiento.objects.filter(maestro=eliminar), 'maestro', conservar)
        count += self._reapuntar_fk(FUP.objects.filter(maestro=eliminar), 'maestro', conservar)
        count += self._reapuntar_fk(RegistroCorrespondencia.objects.filter(maestro=eliminar), 'maestro', conservar)
        count += self._reapuntar_fk(Maestro.objects.filter(maestro_principal=eliminar), 'maestro_principal', conservar)

        return count

    def _reapuntar_fk(self, queryset, field_name, nuevo_objeto):
        count = queryset.count()
        if count > 0:
            queryset.update(**{field_name: nuevo_objeto})
        return count
