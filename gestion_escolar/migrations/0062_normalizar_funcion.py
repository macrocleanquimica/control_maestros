# Normaliza el campo `Maestro.funcion` a los valores canónicos de FUNCION_OPCIONES.
# Antes: había 35% de registros con variantes desnormalizadas
# (espacios antes de "(A)", tildes inconsistentes, " (A)" vs "(A)", None/vacío).
# Se unifica todo al formato canónico "PALABRA(A)" sin espacio antes del paréntesis.

from django.db import migrations

MAPEO = {
    'DIRECTOR': 'DIRECTOR(A)',
    'DIRECTOR (A)': 'DIRECTOR(A)',
    'APOYO TECNICO PEDAGOGICO': 'APOYO TÉCNICO PEDAGÓGICO',
    'MÉDICO (A)': 'MÉDICO(A)',
    'PSICÓLOGO (A)': 'PSICÓLOGO(A)',
    'SECRETARIA ': 'SECRETARIO(A)',
    'SECRETARIO': 'SECRETARIO(A)',
    'SECRETARIO (A)': 'SECRETARIO(A)',
    'TERAPISTA FISICO ': 'TERAPISTA FÍSICO',
    'TRABAJADOR (A) SOCIAL': 'TRABAJADOR(A) SOCIAL',
    'MAESTRO (A) DE COMUNICACIÓN': 'MAESTRO(A) DE COMUNICACIÓN',
    'MAESTRO(A) DE COMUNICACIÓN ': 'MAESTRO(A) DE COMUNICACIÓN',
    'MAESTRO (A) DE GRUPO ESPECIALISTA': 'MAESTRO(A) DE GRUPO ESPECIALISTA',
    'MAESTRO DE TALLER': 'MAESTRO(A) DE TALLER',
    'INSTRUCTOR(A) DE TALLER': 'MAESTRO(A) DE TALLER',
    'MAESTRO(A) MUSICA': 'MAESTRO(A) MÚSICA',
    'OFICIAL DE SERVICIOS DE MANTENIMIENTO': 'OFICIAL DE SERVICIOS Y MANTENIMIENTO',
    'MAESTRO(A) EDUCACION ARTISTICA': 'MAESTRO(A) DE EDUCACIÓN ARTÍSTICA',
    'MAESTRO(A) TERAPIA FÍSICA': 'TERAPISTA FÍSICO',
}
VALORES_SIN_MAPA = {
    'ADMINISTRATIVO ESPECIALIZADO',
    'APOYO TÉCNICO PEDAGÓGICO',
    'ASESOR JURÍDICO',
    'ASISTENTE DE SERVICIOS',
    'AUXILIAR DE GRUPO',
    'BIBLIOTECARIO',
    'DIRECTOR(A)',
    'INTENDENTE',
    'MAESTRO(A) AULA HOSPITALARIA',
    'MAESTRO(A) DE COMUNICACIÓN',
    'MAESTRO(A) DE EDUCACIÓN ARTÍSTICA',
    'MAESTRO(A) DE EDUCACIÓN FÍSICA',
    'MAESTRO(A) DE GRUPO',
    'MAESTRO(A) DE GRUPO CON ESPECIALIDAD',
    'MAESTRO(A) DE GRUPO ESPECIALISTA',
    'MAESTRO(A) DE TALLER',
    'MAESTRO(A) ESPECIALISTA DOCENTE DE APOYO',
    'MAESTRO(A) MÚSICA',
    'MÉDICO(A)',
    'NIÑERO(A)',
    'NO ESPECIFICADO',
    'OFICIAL DE SERVICIOS Y MANTENIMIENTO',
    'OTRO',
    'PROMOTOR TIC',
    'PSICÓLOGO(A)',
    'SECRETARIO(A)',
    'SUPERVISOR(A)',
    'TERAPISTA FÍSICO',
    'TRABAJADOR(A) SOCIAL',
    'VELADOR',
    'VIGILANTE',
}


def normalizar_funcion(apps, schema_editor):
    Maestro = apps.get_model('gestion_escolar', 'Maestro')
    for valor_viejo, valor_nuevo in MAPEO.items():
        Maestro.objects.filter(funcion=valor_viejo).update(funcion=valor_nuevo)
    Maestro.objects.filter(funcion__isnull=True).update(funcion='NO ESPECIFICADO')
    Maestro.objects.filter(funcion='').update(funcion='NO ESPECIFICADO')


def revertir(apps, schema_editor):
    # La normalización no es reversible de forma fiable (se perdieron distinciones
    # como INSTRUCTOR->MAESTRO(A) DE TALLER). Se deja sin operación de reversa.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_escolar', '0061_plantillatramite_liberacion_supervisores'),
    ]

    operations = [
        migrations.RunPython(normalizar_funcion, revertir),
    ]