from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from ..models import RegistroCorrespondencia
from ..forms import RegistroCorrespondenciaForm

class RegistroCorrespondenciaListView(LoginRequiredMixin, ListView):
    model = RegistroCorrespondencia
    template_name = 'gestion_escolar/registrocorrespondencia_list.html'
    context_object_name = 'registros'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Registro de Correspondencia'
        return context

class RegistroCorrespondenciaCreateView(LoginRequiredMixin, CreateView):
    model = RegistroCorrespondencia
    form_class = RegistroCorrespondenciaForm
    template_name = 'gestion_escolar/registrocorrespondencia_form.html'
    success_url = reverse_lazy('registrocorrespondencia_list')

class RegistroCorrespondenciaDetailView(LoginRequiredMixin, DetailView):
    model = RegistroCorrespondencia
    template_name = 'gestion_escolar/registrocorrespondencia_detail.html'
    context_object_name = 'registro'

class RegistroCorrespondenciaUpdateView(LoginRequiredMixin, UpdateView):
    model = RegistroCorrespondencia
    form_class = RegistroCorrespondenciaForm
    template_name = 'gestion_escolar/registrocorrespondencia_form.html'
    success_url = reverse_lazy('registrocorrespondencia_list')

class RegistroCorrespondenciaDeleteView(LoginRequiredMixin, DeleteView):
    model = RegistroCorrespondencia
    template_name = 'gestion_escolar/registrocorrespondencia_confirm_delete.html'
    success_url = reverse_lazy('registrocorrespondencia_list')
