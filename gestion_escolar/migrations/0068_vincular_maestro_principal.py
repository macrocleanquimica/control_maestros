# Vincula las plazas del mismo maestro mediante `maestro_principal`.
#
# Regla de negocio:
#   - Una persona (CURP) puede tener varias plazas (claves presupuestales).
#   - Elegimos como PABLO RAÍZ (maestro_principal) el registro con menor id_maestro
#     de cada CURP con el MISMO nombre exacto (paterno+materno+nombres normalizados).
#   - Solo se SEGUROS si el nombre coincide en todo el grupo (evita typos).
#   - Los grupos con nombres divergentes se OMITEN (revisión manual).
#   - No se sobrescribe a los registros que ya tienen maestro_principal.
#   - No se modifica nada más (id_maestro, clave_presupuestal, funcion, status, tramites).
#
# Se homologan los nombres usando unidecode (ignorar tildes y mayúsculas).
# Como unidecode no está disponible en el historial de migraciones, se usa una
# normalización simple con unicodedata que NO depende de librerías externas.

from django.db import migrations
import unicodedata, re


def _norm(v):
    if not v:
        return ''
    s = unicodedata.normalize('NFKD', str(v)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', s).strip()


def vincular(apps, schema_editor):
    Maestro = apps.get_model('gestion_escolar', 'Maestro')
    from django.db.models import Count

    # Grupos de CURP con 2 o más registros y CURP no vacía
    grupos = (Maestro.objects.exclude(curp__isnull=True).exclude(curp='')
              .values('curp').annotate(n=Count('id_maestro')).filter(n__gt=1))

    vinculados = 0
    for g in grupos:
        ms = list(Maestro.objects.filter(curp=g['curp']).order_by('id_maestro'))
        # Firma de identidad: paterno + materno + nombres normalizados
        firmas = {_norm(m.a_paterno) + '|' + _norm(m.a_materno) + '|' + _norm(m.nombres) for m in ms}
        if len(firmas) != 1:
            # Nombres divergentes -> se omite (revisión manual)
            continue
        raiz = ms[0]  # menor id_maestro (ya ordenado por id)
        for m in ms[1:]:
            if m.maestro_principal_id is None:
                m.maestro_principal = raiz
                m.save(update_fields=['maestro_principal'])
                vinculados += 1
    # La salida se reporta vía schema_editor no soportado; se ignora aquí.

    # Nota: el conteo se imprime por la consola de migración sólo como referencia.
    print(f"[0068] Vinculados {vinculados} plazas secundarias.")


def revertir(apps, schema_editor):
    # Reversa: deshacer sólo lo que esta migración creó no es distinguible de
    # vínculos previos. Se deja sin operación de reversa fiable.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0067_clasificar_no_especificado'),
    ]

    operations = [
        migrations.RunPython(vincular, revertir),
    ]