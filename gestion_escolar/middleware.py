from django.shortcuts import redirect
from django.urls import reverse

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Lista de URLs que no requieren autenticación
        self.exempt_urls = [
            reverse('login'),
            reverse('signup'),
            # Agrega aquí otras URLs que quieras exentar, como 'password_reset', etc.
        ]

    def __call__(self, request):
        # Si el usuario no está autenticado y la URL no está en la lista de exentos
        if not request.user.is_authenticated and request.path not in self.exempt_urls:
            # Redirigir al login, añadiendo la página actual como parámetro 'next'
            # para que el usuario sea redirigido de vuelta después de iniciar sesión.
            return redirect(f"{reverse('login')}?next={request.path}")

        response = self.get_response(request)
        return response
