import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count

from ..models import Zona, Escuela, Maestro, Pendiente, RegistroCorrespondencia

@login_required
def index(request):
    context = {
        'titulo': 'Dashboard'
    }

    # Check permissions for each section
    if request.user.has_perm('gestion_escolar.ver_estadisticas_generales'):
        context['total_zonas'] = Zona.objects.count()
        context['total_escuelas'] = Escuela.objects.count()
        context['total_maestros'] = Maestro.objects.count()
        context['total_directores'] = Maestro.objects.filter(funcion__icontains='DIRECTOR').count()

    if request.user.has_perm('gestion_escolar.ver_lista_pendientes'):
        today = timezone.now().date()
        context['ultimos_pendientes'] = Pendiente.objects.filter(
            usuario=request.user,
            completado=False,
            fecha_programada__lte=today
        ).order_by('fecha_programada')[:5]

    if request.user.has_perm('gestion_escolar.ver_lista_ultimo_personal'):
        context['ultimo_personal'] = Maestro.objects.order_by('-fecha_registro')[:5]

    if request.user.has_perm('gestion_escolar.ver_ultima_correspondencia'):
        context['ultima_correspondencia'] = RegistroCorrespondencia.objects.order_by('-fecha_registro')[:5]

    return render(request, 'gestion_escolar/index.html', context)
