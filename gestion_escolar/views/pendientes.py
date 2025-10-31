from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import CreateView, ListView
from django.urls import reverse_lazy
from django.utils import timezone

from ..models import Pendiente
from ..forms import PendienteForm

class PendienteCreateView(LoginRequiredMixin, CreateView):
    form_class = PendienteForm
    template_name = 'gestion_escolar/pendiente_form.html'
    success_url = reverse_lazy('pendientes_activos')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, "Pendiente creado correctamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nuevo Pendiente'
        return context

class PendienteActiveListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestion_escolar.acceder_pendientes'
    model = Pendiente
    template_name = 'gestion_escolar/pendiente_list.html'
    context_object_name = 'pendientes'

    def get_queryset(self):
        today = timezone.now().date()
        return Pendiente.objects.filter(
            usuario=self.request.user,
            completado=False,
            fecha_programada__lte=today
        ).order_by('fecha_programada')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Mis Pendientes Activos'
        context['vista_todos'] = False
        return context

class PendienteAllListView(LoginRequiredMixin, ListView):
    model = Pendiente
    template_name = 'gestion_escolar/pendiente_list.html'
    context_object_name = 'pendientes'

    def get_queryset(self):
        return Pendiente.objects.filter(usuario=self.request.user).order_by('-fecha_programada')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Todos Mis Pendientes'
        context['vista_todos'] = True
        return context

@login_required
def pendiente_marcar_completado(request, pk):
    if request.method == 'POST':
        pendiente = get_object_or_404(Pendiente, pk=pk, usuario=request.user)
        pendiente.completado = True
        pendiente.save()
        messages.success(request, f"El pendiente '{pendiente.titulo}' ha sido marcado como completado.")
        return redirect('pendientes_activos')
    else:
        return redirect('pendientes_activos')
