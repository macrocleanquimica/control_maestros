from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Correspondencia, Notificacion

@receiver(post_save, sender=Correspondencia)
def crear_notificacion_mensaje(sender, instance, created, **kwargs):
    """
    Crea una notificación para el destinatario cuando se envía un nuevo mensaje de correspondencia.
    """
    if created:
        Notificacion.objects.create(
            usuario=instance.destinatario,
            mensaje=f"Has recibido un nuevo mensaje de {instance.remitente.username}: '{instance.asunto}'",
            correspondencia=instance
        )
