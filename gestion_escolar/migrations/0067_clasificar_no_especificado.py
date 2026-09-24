# Clasifica los maestros con funcion='NO ESPECIFICADO' según su centro de trabajo (C.T.):
#   - C.T. que empieza por '10DML' -> 'MAESTRO(A) DE GRUPO CON ESPECIALIDAD'
#   - C.T. que empieza por '10FUA' -> 'MAESTRO(A) ESPECIALISTA DOCENTE DE APOYO'
# Se EXCLUYEN los maestros con permiso especial (sin función real) que deben
# conservar 'NO ESPECIFICADO':
#   - 01031 ANTONIO HERRERA MONTES (10FSE0012Z SUPERVISIÓN 9)
#   - 00474 DIANA ARACELI SALAS SALAZAR (10FSE0003S SUPERVISIÓN 4)
#   - 01544 ERIKA PATRICIA LIRA BRISEÑO (10FRB0008R PROCURADURÍA)

from django.db import migrations

# Maestros con permiso especial que conservan 'NO ESPECIFICADO'
CONSERVAR = ['01031', '00474', '01544']


def clasificar_no_especificado(apps, schema_editor):
    Maestro = apps.get_model('gestion_escolar', 'Maestro')
    # 10DML -> MAESTRO(A) DE GRUPO CON ESPECIALIDAD
    Maestro.objects.filter(
        funcion='NO ESPECIFICADO',
        id_escuela__id_escuela__startswith='10DML',
    ).exclude(id_maestro__in=CONSERVAR).update(funcion='MAESTRO(A) DE GRUPO CON ESPECIALIDAD')
    # 10FUA -> MAESTRO(A) ESPECIALISTA DOCENTE DE APOYO
    Maestro.objects.filter(
        funcion='NO ESPECIFICADO',
        id_escuela__id_escuela__startswith='10FUA',
    ).exclude(id_maestro__in=CONSERVAR).update(funcion='MAESTRO(A) ESPECIALISTA DOCENTE DE APOYO')


def revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0066_alter_status_opciones'),
    ]

    operations = [
        migrations.RunPython(clasificar_no_especificado, revertir),
    ]