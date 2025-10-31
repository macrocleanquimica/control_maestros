from .models import Tema, Notificacion, Pendiente
from django.utils import timezone
from django.urls import reverse

def active_theme_processor(request):
    """
    Añade el tema activo (si existe) al contexto de todas las plantillas.
    """
    today = timezone.localdate()
    
    # Busca el primer tema activo que coincida con el rango de fechas
    active_theme = Tema.objects.filter(
        activo=True,
        fecha_inicio__lte=today,
        fecha_fin__gte=today
    ).first()
    
    return {'active_theme': active_theme}

def notifications_processor(request):
    """
    Añade notificaciones y pendientes al contexto de todas las plantillas.
    """
    if not request.user.is_authenticated:
        return {'global_alerts': [], 'total_alerts': 0}

    global_alerts = []
    today = timezone.now().date()

    # 1. Obtener notificaciones de mensajes no leídos
    unread_messages = Notificacion.objects.filter(usuario=request.user, leida=False)
    for msg in unread_messages:
        global_alerts.append({
            'type': 'message',
            'text': msg.mensaje,
            'date': msg.fecha_creacion,
            'url': reverse('correspondencia_detail', args=[msg.correspondencia.id]) if msg.correspondencia else '#'
        })

    # 2. Obtener pendientes vencidos o para hoy
    due_tasks = Pendiente.objects.filter(usuario=request.user, completado=False, fecha_programada__lte=today)
    for task in due_tasks:
        global_alerts.append({
            'type': 'task',
            'text': f"Pendiente: {task.titulo}",
            'date': task.fecha_programada,
            'url': reverse('pendientes_activos')
        })

    return {'global_alerts': global_alerts, 'total_alerts': len(global_alerts)}