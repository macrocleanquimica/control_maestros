from django.apps import AppConfig

class GestionEscolarConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestion_escolar'

    def ready(self):
        import gestion_escolar.signals
