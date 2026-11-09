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

    def get_queryset(self):
        return Group.objects.prefetch_related('permissions', 'permissions__content_type', 'user_set')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Gestión de Roles y Permisos'
        context['users'] = User.objects.all()
        # Calcular estadísticas
        users_with_roles = User.objects.filter(groups__isnull=False).distinct().count()
        users_without_roles = User.objects.filter(groups__isnull=True).count()
        context['users_with_roles'] = users_with_roles
        context['users_without_roles'] = users_without_roles
        context['users_activos'] = User.objects.filter(is_active=True).count()
        # Resumen de permisos por rol para las tarjetas (sin entrar a cada uno).
        context['roles_info'] = [
            {'role': r, 'resumen': resumir_permisos_rol(r)} for r in context['roles']
        ]
        return context


# Etiquetas cortas para los accesos a módulos en las tarjetas de rol.
MODULOS_CORTO = {
    'acceder_oficios': 'Oficios',
    'acceder_tramites': 'Trámites',
    'acceder_vacancias': 'Vacancia',
    'acceder_historial': 'Historial',
    'acceder_ajustes': 'Ajustes',
    'acceder_bandeja_entrada': 'Bandeja',
    'acceder_reportes': 'Reportes',
    'acceder_pendientes': 'Pendientes',
    'acceder_fup': 'FUP',
    'acceder_kardex': 'Kardex',
    'acceder_prelacion': 'Prelación',
}


def resumir_permisos_rol(role):
    """Resume qué puede hacer un rol: módulos de acceso + CRUD por modelo."""
    accesos = []
    crud = []
    for perm in role.permissions.all():
        if perm.codename in MODULOS_CORTO:
            accesos.append(MODULOS_CORTO[perm.codename])
        elif perm.codename.startswith(('add_', 'change_', 'delete_', 'view_')):
            accion = perm.codename.split('_')[0]
            crud.append((perm.content_type.name, accion))
    accesos = sorted(set(accesos))
    por_modelo = {}
    for modelo, accion in crud:
        por_modelo.setdefault(modelo, set()).add(accion)
    detalle = [
        {'modelo': modelo, 'acciones': ''.join(a[0].upper() for a in ('view', 'add', 'change', 'delete') if a in accs)}
        for modelo, accs in sorted(por_modelo.items())
    ]
    return {'accesos': accesos, 'crud': detalle}

# Sección de la matriz para cada modelo (por content_type.model).
SECCION_POR_MODELO = {
    'maestro': 'Personal',
    'zona': 'Catálogos',
    'escuela': 'Catálogos',
    'escuelaregular': 'Catálogos',
    'categoria': 'Catálogos',
    'incentivo': 'Catálogos',
    'motivotramite': 'Catálogos',
    'plantillatramite': 'Catálogos',
    'tipoapreciacion': 'Catálogos',
    'prelacion': 'Catálogos',
    'vacancia': 'Trámites y movimientos',
    'lotereportevacancia': 'Trámites y movimientos',
    'historial': 'Trámites y movimientos',
    'kardexmovimiento': 'Trámites y movimientos',
    'fup': 'Trámites y movimientos',
    'documentoexpediente': 'Trámites y movimientos',
    'interinato': 'Trámites y movimientos',
    'correspondencia': 'Trámites y movimientos',
    'registrocorrespondencia': 'Trámites y movimientos',
    'pendiente': 'Trámites y movimientos',
    'notificacion': 'Trámites y movimientos',
    'tema': 'Trámites y movimientos',
}
ORDEN_SECCIONES = ['Personal', 'Catálogos', 'Trámites y movimientos', 'Módulos']


def get_permissions_matrix():
    """Matriz de permisos generada dinámicamente (no hay lista fija que mantener).

    - Modelos con tabla (managed): una fila CRUD (Ver/Agregar/Editar/Eliminar).
    - Modelos ancla sin tabla (managed=False: Modulo*): cada permiso como
      fila de acceso directo. Así los módulos nuevos aparecen solos.
    Devuelve secciones [{seccion, items}] para la plantilla.
    """
    from django.apps import apps

    por_seccion = {}
    ordered_models = [
        'zona', 'escuela', 'maestro', 'categoria',
        'historial', 'pendiente', 'correspondencia', 'registrocorrespondencia', 'fup',
    ]

    content_types = {ct.model: ct for ct in ContentType.objects.filter(app_label='gestion_escolar')}

    def fila_crud(ct):
        perms = Permission.objects.filter(content_type=ct)
        return {
            'model_name': ct.name,
            'type': 'crud',
            'view': perms.filter(codename__startswith='view_').first(),
            'add': perms.filter(codename__startswith='add_').first(),
            'change': perms.filter(codename__startswith='change_').first(),
            'delete': perms.filter(codename__startswith='delete_').first(),
        }

    def clase_modelo(model_name):
        try:
            return apps.get_model('gestion_escolar', model_name)
        except LookupError:
            return None

    def colocar(model_name, item):
        seccion = SECCION_POR_MODELO.get(model_name, 'Otros')
        por_seccion.setdefault(seccion, []).append(item)

    vistos = set()

    def agregar_modelo(model_name):
        ct = content_types.get(model_name)
        if ct is None or model_name in vistos:
            return
        model_cls = clase_modelo(model_name)
        if model_cls is None:
            # ContentType huérfano (modelo eliminado): no se muestra.
            return
        vistos.add(model_name)
        if model_cls._meta.managed:
            colocar(model_name, fila_crud(ct))
        else:
            # Ancla de módulo (sin tabla): solo sus permisos propios
            # (acceder_*, ver_*); se ignoran los add/change/delete/view
            # residuales que Django pudo haber creado.
            customs = (
                Permission.objects.filter(content_type=ct)
                .exclude(codename__startswith='add_')
                .exclude(codename__startswith='change_')
                .exclude(codename__startswith='delete_')
                .exclude(codename__startswith='view_')
                .order_by('codename')
            )
            for perm in customs:
                colocar(model_name, {
                    'model_name': perm.name,
                    'type': 'custom',
                    'permission': perm
                })

    for model_name in ordered_models:
        agregar_modelo(model_name)
    for model_name in sorted(content_types):
        agregar_modelo(model_name)

    secciones = [
        {'seccion': nombre, 'items': por_seccion[nombre]}
        for nombre in ORDEN_SECCIONES + sorted(set(por_seccion) - set(ORDEN_SECCIONES))
        if nombre in por_seccion
    ]
    return secciones

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
