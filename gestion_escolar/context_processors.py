from .models import Notificacion, Pendiente
from django.utils import timezone
from django.urls import reverse

def notifications_processor(request):
    if not request.user.is_authenticated:
        return {}

    alerts = []
    today = timezone.now().date()
    
    # Obtener notificaciones de mensajes no leídas
    unread_notifications = Notificacion.objects.filter(usuario=request.user, leida=False).select_related('correspondencia')
    for notification in unread_notifications:
        if notification.correspondencia:
            alerts.append({
                'type': 'message',
                'text': notification.mensaje,
                'date': notification.fecha_creacion,
                'url': reverse('correspondencia_detail', args=[notification.correspondencia.pk])
            })
    
    # Obtener pendientes activos cuya fecha programada ha llegado
    active_pendientes = Pendiente.objects.filter(
        usuario=request.user,
        completado=False,
        fecha_programada__lte=today
    )
    for pendiente in active_pendientes:
        alerts.append({
            'type': 'task',
            'text': f"Pendiente: {pendiente.titulo}",
            'date': pendiente.fecha_programada,
            'url': reverse('pendientes_activos')
        })

    # Ordenar alertas por fecha, las más nuevas primero
    alerts.sort(key=lambda x: x['date'], reverse=True)
    
    return {
        'global_alerts': alerts,
        'total_alerts': len(alerts),
    }