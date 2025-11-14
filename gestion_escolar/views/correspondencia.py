from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date

from ..models import RegistroCorrespondencia
from ..forms import RegistroCorrespondenciaForm

class RegistroCorrespondenciaListView(LoginRequiredMixin, ListView):
    model = RegistroCorrespondencia
    template_name = 'gestion_escolar/registrocorrespondencia_list.html'
    context_object_name = 'registros'

    def get_queryset(self):
        # Por defecto, ordena por los más recientes primero
        queryset = super().get_queryset().order_by('-fecha_recibido', '-id')
        
        # Obtener fechas del request GET
        fecha_inicio_str = self.request.GET.get('fecha_inicio')
        fecha_fin_str = self.request.GET.get('fecha_fin')

        # Aplicar filtro de fecha de inicio si existe
        if fecha_inicio_str:
            fecha_inicio = parse_date(fecha_inicio_str)
            if fecha_inicio:
                queryset = queryset.filter(fecha_recibido__gte=fecha_inicio)

        # Aplicar filtro de fecha de fin si existe
        if fecha_fin_str:
            fecha_fin = parse_date(fecha_fin_str)
            if fecha_fin:
                queryset = queryset.filter(fecha_recibido__lte=fecha_fin)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Registro de Correspondencia'
        # Devolver los valores del filtro a la plantilla para mantener el estado
        context['fecha_inicio'] = self.request.GET.get('fecha_inicio', '')
        context['fecha_fin'] = self.request.GET.get('fecha_fin', '')
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
