from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.models import Group, User, Permission
from django.contrib.contenttypes.models import ContentType

from ..models import Tema
from ..forms import RolePermissionForm, TemaForm

class RoleListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Group
    template_name = 'gestion_escolar/ajustes/role_list.html'
    context_object_name = 'roles'

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Gestión de Roles y Permisos'
        context['users'] = User.objects.all()
        # Calcular estadísticas
        users_with_roles = User.objects.filter(groups__isnull=False).distinct().count()
        users_without_roles = User.objects.filter(groups__isnull=True).count()
        context['users_with_roles'] = users_with_roles
        context['users_without_roles'] = users_without_roles
        return context

def get_permissions_matrix():
    matrix = []
    ordered_models = [
        'zona', 'escuela', 'maestro', 'categoria', 
        'historial', 'pendiente', 'correspondencia', 'registrocorrespondencia', 'fup'
    ]
    
    app_models = ContentType.objects.filter(app_label='gestion_escolar').order_by('model')

    for model_name in ordered_models:
        try:
            ct = app_models.get(model=model_name)
            perms = Permission.objects.filter(content_type=ct)
            matrix.append({
                'model_name': ct.name,
                'type': 'crud',
                'view': perms.filter(codename__startswith='view_').first(),
                'add': perms.filter(codename__startswith='add_').first(),
                'change': perms.filter(codename__startswith='change_').first(),
                'delete': perms.filter(codename__startswith='delete_').first(),
            })
        except ContentType.DoesNotExist:
            continue

    custom_perms_codenames = [
        'acceder_oficios', 'acceder_tramites', 'acceder_vacancias', 
        'acceder_historial', 'acceder_ajustes', 'acceder_bandeja_entrada',
        'acceder_reportes', 'acceder_pendientes',
        'ver_estadisticas_generales', 'ver_grafico_distribucion_zona',
        'ver_lista_pendientes', 'ver_lista_ultimo_personal', 'ver_ultima_correspondencia',
        'acceder_kardex', 'acceder_fup',
    ]
    
    for codename in custom_perms_codenames:
        try:
            perm = Permission.objects.get(codename=codename)
            matrix.append({
                'model_name': perm.name,
                'type': 'custom',
                'permission': perm
            })
        except Permission.DoesNotExist:
            continue
            
    return matrix

class RoleCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Group
    form_class = RolePermissionForm
    template_name = 'gestion_escolar/ajustes/role_form.html'
    success_url = reverse_lazy('role_list')

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nuevo Rol'
        context['permissions_matrix'] = get_permissions_matrix()
        return context

class RoleUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Group
    form_class = RolePermissionForm
    template_name = 'gestion_escolar/ajustes/role_form.html'
    success_url = reverse_lazy('role_list')

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar Rol: {self.object.name}'
        context['permissions_matrix'] = get_permissions_matrix()
        return context

@login_required
@user_passes_test(lambda u: u.is_superuser)
def manage_role_members(request, pk):
    role = get_object_or_404(Group, pk=pk)
    users_in_role = role.user_set.all()
    users_not_in_role = User.objects.exclude(groups=role)

    if request.method == 'POST':
        users_to_add = request.POST.getlist('users_to_add')
        users_to_remove = request.POST.getlist('users_to_remove')

        for user_id in users_to_add:
            user = User.objects.get(pk=user_id)
            user.groups.add(role)
        
        for user_id in users_to_remove:
            user = User.objects.get(pk=user_id)
            user.groups.remove(role)
        
        messages.success(request, 'Miembros del rol actualizados correctamente.')
        return redirect('role_members', pk=pk)

    context = {
        'titulo': f'Gestionar Miembros del Rol: {role.name}',
        'role': role,
        'members': users_in_role,
        'non_members': users_not_in_role
    }
    return render(request, 'gestion_escolar/ajustes/role_members.html', context)

class ThemeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Tema
    template_name = 'gestion_escolar/ajustes/tema_list.html'
    context_object_name = 'temas'
    permission_required = 'gestion_escolar.view_tema'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Gestión de Temas de Personalización'
        return context

class ThemeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Tema
    form_class = TemaForm
    template_name = 'gestion_escolar/ajustes/tema_form.html'
    success_url = reverse_lazy('tema_list')
    permission_required = 'gestion_escolar.add_tema'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nuevo Tema'
        return context

class ThemeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Tema
    form_class = TemaForm
    template_name = 'gestion_escolar/ajustes/tema_form.html'
    success_url = reverse_lazy('tema_list')
    permission_required = 'gestion_escolar.change_tema'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar Tema: {self.object.nombre}'
        return context

class ThemeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Tema
    template_name = 'gestion_escolar/ajustes/tema_confirm_delete.html'
    success_url = reverse_lazy('tema_list')
    permission_required = 'gestion_escolar.delete_tema'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Confirmar Eliminación de Tema: {self.object.nombre}'
        return context

class RoleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Group
    template_name = 'gestion_escolar/ajustes/role_confirm_delete.html'
    success_url = reverse_lazy('role_list')
    def test_func(self):
        return self.request.user.is_superuser
