from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from ..models import Correspondencia
from ..forms import CorrespondenciaForm

class CorrespondenciaInboxView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestion_escolar.acceder_bandeja_entrada'
    model = Correspondencia
    template_name = 'gestion_escolar/correspondencia_inbox.html'
    context_object_name = 'mensajes'

    def get_queryset(self):
        return Correspondencia.objects.filter(destinatario=self.request.user).order_by('-fecha_creacion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Bandeja de Entrada'
        return context

class CorrespondenciaDetailView(LoginRequiredMixin, DetailView):
    model = Correspondencia
    template_name = 'gestion_escolar/correspondencia_detail.html'
    context_object_name = 'mensaje'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.destinatario == self.request.user:
            if not obj.leido:
                obj.leido = True
                obj.save()
            return obj
        else:
            raise PermissionDenied("No tienes permiso para ver este mensaje.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = self.object.asunto
        return context

@login_required
def correspondencia_eliminar(request, pk):
    if request.method == 'POST':
        mensaje = get_object_or_404(Correspondencia, pk=pk)
        if mensaje.destinatario == request.user:
            mensaje.delete()
            messages.success(request, "Mensaje eliminado correctamente.")
        else:
            messages.error(request, "No tienes permiso para eliminar este mensaje.")
    return redirect('correspondencia_inbox')

class CorrespondenciaCreateView(LoginRequiredMixin, CreateView):
    form_class = CorrespondenciaForm
    template_name = 'gestion_escolar/correspondencia_form.html'
    success_url = reverse_lazy('correspondencia_inbox')

    def form_valid(self, form):
        form.instance.remitente = self.request.user
        messages.success(self.request, "Mensaje enviado correctamente.")
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['destinatario'].queryset = User.objects.exclude(pk=self.request.user.pk)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Redactar Nuevo Mensaje'
        return context
