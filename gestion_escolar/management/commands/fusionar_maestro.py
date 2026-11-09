from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestion_escolar.models import Maestro

# Campos que no se copian del registro que se elimina.
CAMPOS_EXCLUIDOS = {
    'id_maestro',
    'user',
    'maestro_principal',
    'fecha_registro',
    'fecha_actualizacion',
    'clave_presupuestal',
    'a_paterno_normalized',
    'a_materno_normalized',
    'nombres_normalized',
    'nombre_completo_normalized',
    'nombre_completo_unaccented',
}

VACIOS = (None, '')


class Command(BaseCommand):
    help = (
        'Fusiona dos registros de maestro: re-apunta todas las relaciones al registro '
        'que se conserva, completa sus campos vacios con los del otro registro y elimina '
        'el registro duplicado.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--conservar', required=True, help='ID del maestro que se conserva (ej. 01503)')
        parser.add_argument('--eliminar', required=True, help='ID del maestro duplicado que se elimina (ej. 01504)')
        parser.add_argument(
            '--preferir-eliminar',
            default='',
            help='Campos separados por coma cuyos valores se toman del registro que se elimina '
                 'aunque el que se conserva ya tenga valor (ej. sexo,nivel_estudio).',
        )
        parser.add_argument(
            '--seco',
            action='store_true',
            help='Solo muestra lo que haria, sin modificar la base de datos.',
        )

    def handle(self, *args, **options):
        try:
            conservar = Maestro.objects.get(pk=options['conservar'])
        except Maestro.DoesNotExist:
            raise CommandError(f'No existe el maestro {options["conservar"]}.')
        try:
            eliminar = Maestro.objects.get(pk=options['eliminar'])
        except Maestro.DoesNotExist:
            raise CommandError(f'No existe el maestro {options["eliminar"]}.')

        if conservar.pk == eliminar.pk:
            raise CommandError('Los IDs de --conservar y --eliminar deben ser distintos.')

        eliminar_id = eliminar.pk

        preferir = {c.strip() for c in options['preferir_eliminar'].split(',') if c.strip()}
        desconocidos = preferir - {f.name for f in Maestro._meta.concrete_fields}
        if desconocidos:
            raise CommandError(f'Campos desconocidos en --preferir-eliminar: {", ".join(sorted(desconocidos))}')

        self.stdout.write(self.style.SUCCESS('Fusion de maestros'))
        self.stdout.write(f'  Conservar: {conservar.pk} - {conservar}')
        self.stdout.write(f'  Eliminar:  {eliminar.pk} - {eliminar}')

        relaciones = self._relaciones()
        movimientos = []
        conflictos = []

        for modelo, campo in relaciones:
            campo_fk = modelo._meta.get_field(campo)
            qs = modelo.objects.filter(**{campo: eliminar})
            total = qs.count()
            if not total:
                continue
            choques = [obj for obj in qs if self._choca_unico(modelo, campo_fk, obj, conservar)]
            movimientos.append((modelo._meta.label, campo, total))
            if choques:
                conflictos.append((modelo._meta.label, campo, choques))

        if conflictos:
            for etiqueta, campo, choques in conflictos:
                ids = ', '.join(str(obj.pk) for obj in choques[:10])
                self.stderr.write(self.style.ERROR(
                    f'Conflicto de unicidad en {etiqueta}.{campo} (IDs: {ids}). No se modifico nada.'
                ))
            raise CommandError('Hay relaciones que chocarian con restricciones unique; resuelvelas primero.')

        self.stdout.write('\nRelaciones a re-apuntar:')
        if movimientos:
            for etiqueta, campo, total in movimientos:
                self.stdout.write(f'  {etiqueta}.{campo}: {total}')
        else:
            self.stdout.write('  (ninguna)')

        cambios = self._calcular_cambios(conservar, eliminar, preferir)
        self.stdout.write('\nCampos a completar en el registro conservado:')
        if cambios:
            for nombre, antes, despues in cambios:
                self.stdout.write(f'  {nombre}: {antes!r} -> {despues!r}')
        else:
            self.stdout.write('  (ninguno)')

        if options['seco']:
            self.stdout.write(self.style.WARNING('\nModo seco: no se guardo ningun cambio.'))
            return

        with transaction.atomic():
            for modelo, campo in relaciones:
                modelo.objects.filter(**{campo: eliminar}).update(**{campo: conservar})

            # Si el registro conservado era plaza secundaria del que se elimina, se vuelve principal.
            if conservar.maestro_principal_id == eliminar.pk:
                conservar.maestro_principal = None

            # Mover el usuario vinculado, si el registro conservado no tiene uno.
            if conservar.user_id is None and eliminar.user_id is not None:
                User = apps.get_model('auth', 'User')
                User.objects.filter(pk=eliminar.user_id).update(maestro_profile=conservar)
                conservar.refresh_from_db(fields=['user'])

            for nombre, _antes, despues in cambios:
                setattr(conservar, nombre, despues)

            conservar.save()
            eliminar.delete()

        self.stdout.write(self.style.SUCCESS(
            f'\nListo. Se conservo {conservar.pk} ({conservar}) y se elimino {eliminar_id}.'
        ))

    def _relaciones(self):
        """Devuelve pares (modelo, nombre_de_campo_fk) que apuntan a Maestro."""
        relaciones = []
        for modelo in apps.get_models():
            if modelo._meta.auto_created:
                continue
            for campo in modelo._meta.concrete_fields:
                if not campo.is_relation or campo.many_to_many or campo.auto_created:
                    continue
                if campo.related_model is not Maestro:
                    continue
                if modelo is Maestro and campo.name == 'maestro_principal':
                    relaciones.append((modelo, campo.name))
                elif modelo is not Maestro and campo.many_to_one:
                    relaciones.append((modelo, campo.name))
        return relaciones

    def _choca_unico(self, modelo, campo_fk, obj, conservar):
        """Indica si re-apuntar obj a conservar violaria una restriccion unique."""
        campos = []
        for conjunto in modelo._meta.unique_together:
            if campo_fk.name in conjunto:
                campos.append(tuple(conjunto))
        for restriccion in modelo._meta.constraints:
            fields = getattr(restriccion, 'fields', None)
            if fields and campo_fk.name in fields:
                campos.append(tuple(fields))
        if not campos:
            return False

        for conjunto in campos:
            filtro = {}
            for nombre in conjunto:
                if nombre == campo_fk.name:
                    filtro[nombre] = conservar
                else:
                    filtro[nombre] = getattr(obj, modelo._meta.get_field(nombre).attname)
            if modelo.objects.filter(**filtro).exclude(pk=obj.pk).exists():
                return True
        return False

    def _calcular_cambios(self, conservar, eliminar, preferir):
        cambios = []
        for campo in Maestro._meta.concrete_fields:
            if campo.name in CAMPOS_EXCLUIDOS:
                continue
            actual = getattr(conservar, campo.attname)
            nuevo = getattr(eliminar, campo.attname)

            if campo.name == 'observaciones':
                if nuevo not in VACIOS and actual not in VACIOS and actual != nuevo:
                    cambios.append((campo.name, actual, f'{actual}\n{nuevo}'))
                elif actual in VACIOS and nuevo not in VACIOS:
                    cambios.append((campo.name, actual, nuevo))
                continue

            if campo.name in preferir:
                if nuevo != actual:
                    cambios.append((campo.name, actual, nuevo))
                continue

            if actual in VACIOS and nuevo not in VACIOS:
                cambios.append((campo.name, actual, nuevo))
        return cambios
