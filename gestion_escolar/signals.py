from django.db.models.signals import post_save
from django.db.backends.signals import connection_created
from django.dispatch import receiver
from django.contrib.auth.models import User
from unidecode import unidecode

# Registra la función unaccent para búsquedas insensibles a acentos en SQLite
@receiver(connection_created)
def extend_sqlite(connection=None, **kwargs):
    if connection.vendor == 'sqlite':
        def remove_accents(text):
            return unidecode(str(text))
        connection.connection.create_function('unaccent', 1, remove_accents)

@receiver(post_save, sender='gestion_escolar.Correspondencia')
def crear_notificacion_mensaje(sender, instance, created, **kwargs):
    """
    Crea una notificación para el destinatario cuando se envía un nuevo mensaje de correspondencia.
    """
    if created:
        # Importación lazy para evitar registro duplicado de modelos
        from .models import Notificacion
        
        Notificacion.objects.create(
            usuario=instance.destinatario,
            mensaje=f"Has recibido un nuevo mensaje de {instance.remitente.username}: '{instance.asunto}'",
            correspondencia=instance
        )
