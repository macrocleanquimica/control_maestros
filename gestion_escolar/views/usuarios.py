from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
import json

from ..user_forms import UserCreationFormCustom, UserUpdateFormCustom, AdminPasswordChangeForm
from ..models import Maestro


def is_admin_user(user):
    """
    Verifica si el usuario es administrador:
    - Superusuario, O
    - Staff que pertenece al grupo 'Administrador'
    """
    if user.is_superuser:
        return True
    if user.is_staff and user.groups.filter(name='Administrador').exists():
        return True
    return False


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin para vistas que requieren permisos de administrador"""
    
    def test_func(self):
        return is_admin_user(self.request.user)
    
    def handle_no_permission(self):
        messages.error(self.request, 'No tienes permisos para acceder a esta sección.')
        return redirect('index')


# ==================== VISTAS DE LISTA ====================

class UserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Vista para listar todos los usuarios del sistema"""
    model = User
    template_name = 'gestion_escolar/usuarios/user_list.html'
    context_object_name = 'usuarios'
    paginate_by = 25

    def get_queryset(self):
        queryset = User.objects.all().select_related().prefetch_related('groups')
        
        # Filtro por estado
        estado = self.request.GET.get('estado', 'todos')
        if estado == 'activos':
            queryset = queryset.filter(is_active=True)
        elif estado == 'inactivos':
            queryset = queryset.filter(is_active=False)
        elif estado == 'staff':
            queryset = queryset.filter(is_staff=True)
        elif estado == 'superusuarios':
            queryset = queryset.filter(is_superuser=True)
        
        # Búsqueda
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset.order_by('-date_joined')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_usuarios'] = User.objects.count()
        context['usuarios_activos'] = User.objects.filter(is_active=True).count()
        context['usuarios_inactivos'] = User.objects.filter(is_active=False).count()
        context['estado_actual'] = self.request.GET.get('estado', 'todos')
        context['search_query'] = self.request.GET.get('search', '')
        return context


# ==================== VISTAS DE CREACIÓN ====================

class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Vista para crear un nuevo usuario"""
    model = User
    form_class = UserCreationFormCustom
    template_name = 'gestion_escolar/usuarios/user_form.html'
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'Usuario "{self.object.username}" creado exitosamente.'
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request, 
            'Error al crear el usuario. Por favor, revisa los campos.'
        )
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nuevo Usuario'
        context['boton_texto'] = 'Crear Usuario'
        return context


# ==================== VISTAS DE EDICIÓN ====================

class UserUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Vista para editar un usuario existente"""
    model = User
    form_class = UserUpdateFormCustom
    template_name = 'gestion_escolar/usuarios/user_form.html'
    success_url = reverse_lazy('user_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def form_valid(self, form):
        # Prevenir que un usuario se desactive a sí mismo
        if self.object == self.request.user and not form.cleaned_data.get('is_active'):
            messages.error(self.request, 'No puedes desactivar tu propia cuenta.')
            return self.form_invalid(form)
        
        # Prevenir eliminar el último superusuario
        if self.object.is_superuser and not form.cleaned_data.get('is_superuser'):
            if User.objects.filter(is_superuser=True).count() == 1:
                messages.error(self.request, 'No puedes quitar permisos de superusuario al último superusuario del sistema.')
                return self.form_invalid(form)
        
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'Usuario "{self.object.username}" actualizado exitosamente.'
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request, 
            'Error al actualizar el usuario. Por favor, revisa los campos.'
        )
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Editar Usuario: {self.object.username}'
        context['boton_texto'] = 'Guardar Cambios'
        context['editando'] = True
        return context


# ==================== VISTAS DE DETALLE ====================

class UserDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    """Vista para ver detalles de un usuario"""
    model = User
    template_name = 'gestion_escolar/usuarios/user_detail.html'
    context_object_name = 'usuario'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener maestro vinculado si existe
        try:
            context['maestro_vinculado'] = Maestro.objects.get(user=self.object)
        except Maestro.DoesNotExist:
            context['maestro_vinculado'] = None
        
        # Obtener grupos
        context['grupos'] = self.object.groups.all()
        
        # Obtener permisos específicos del usuario (no heredados de grupos)
        context['permisos_usuario'] = self.object.user_permissions.all()
        
        return context


# ==================== VISTA DE CAMBIO DE CONTRASEÑA ====================

class UserPasswordChangeView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Vista para que un administrador cambie la contraseña de un usuario"""
    model = User
    template_name = 'gestion_escolar/usuarios/user_password_change.html'
    success_url = reverse_lazy('user_list')
    form_class = AdminPasswordChangeForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.object
        # Remover 'instance' porque AdminPasswordChangeForm no lo usa
        kwargs.pop('instance', None)
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request, 
            f'Contraseña de "{self.object.username}" cambiada exitosamente.'
        )
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(
            self.request, 
            'Error al cambiar la contraseña. Por favor, revisa los campos.'
        )
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['usuario'] = self.object
        return context


# ==================== VISTAS AJAX ====================

@login_required
@user_passes_test(is_admin_user)
def user_datatable_ajax(request):
    """Endpoint AJAX para DataTable de usuarios"""
    
    # Parámetros de DataTable
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')
    order_column_index = int(request.GET.get('order[0][column]', 0))
    order_dir = request.GET.get('order[0][dir]', 'asc')
    
    # Filtro por estado
    estado = request.GET.get('estado', 'todos')
    
    # Columnas para ordenamiento
    columns = ['username', 'first_name', 'email', 'is_active', 'date_joined', 'last_login']
    order_column = columns[order_column_index] if order_column_index < len(columns) else 'username'
    
    if order_dir == 'desc':
        order_column = f'-{order_column}'
    
    # Construir queryset
    queryset = User.objects.all()
    
    # Aplicar filtro de estado
    if estado == 'activos':
        queryset = queryset.filter(is_active=True)
    elif estado == 'inactivos':
        queryset = queryset.filter(is_active=False)
    elif estado == 'staff':
        queryset = queryset.filter(is_staff=True)
    elif estado == 'superusuarios':
        queryset = queryset.filter(is_superuser=True)
    
    # Aplicar búsqueda
    if search_value:
        queryset = queryset.filter(
            Q(username__icontains=search_value) |
            Q(first_name__icontains=search_value) |
            Q(last_name__icontains=search_value) |
            Q(email__icontains=search_value)
        )
    
    # Total de registros
    total_records = User.objects.count()
    filtered_records = queryset.count()
    
    # Aplicar ordenamiento y paginación
    queryset = queryset.order_by(order_column)[start:start + length]
    
    # Construir datos
    data = []
    for user in queryset:
        # Obtener grupos
        grupos = ', '.join([g.name for g in user.groups.all()]) or 'Sin grupo'
        
        # Nombre completo
        nombre_completo = f"{user.first_name} {user.last_name}".strip() or '-'
        
        # Estado
        if user.is_active:
            estado_badge = '<span class="badge bg-success">Activo</span>'
        else:
            estado_badge = '<span class="badge bg-danger">Inactivo</span>'
        
        # Permisos
        permisos_badges = ''
        if user.is_superuser:
            permisos_badges += '<span class="badge bg-danger me-1">Superusuario</span>'
        elif user.is_staff:
            permisos_badges += '<span class="badge bg-warning me-1">Staff</span>'
        
        # Último login
        ultimo_login = user.last_login.strftime('%d/%m/%Y %H:%M') if user.last_login else 'Nunca'
        
        # Acciones
        acciones = f'''
            <div class="btn-group btn-group-sm" role="group">
                <a href="/ajustes/usuarios/{user.pk}/detalle/" class="btn btn-info btn-sm" title="Ver Detalles">
                    <i class="fas fa-eye"></i>
                </a>
                <a href="/ajustes/usuarios/{user.pk}/editar/" class="btn btn-primary btn-sm" title="Editar">
                    <i class="fas fa-edit"></i>
                </a>
                <a href="/ajustes/usuarios/{user.pk}/password/" class="btn btn-warning btn-sm" title="Cambiar Contraseña">
                    <i class="fas fa-key"></i>
                </a>
                <button class="btn btn-{'danger' if user.is_active else 'success'} btn-sm toggle-active" 
                        data-user-id="{user.pk}" 
                        data-current-state="{'active' if user.is_active else 'inactive'}"
                        title="{'Desactivar' if user.is_active else 'Activar'}">
                    <i class="fas fa-{'ban' if user.is_active else 'check'}"></i>
                </button>
            </div>
        '''
        
        data.append({
            'username': user.username,
            'nombre_completo': nombre_completo,
            'email': user.email or '-',
            'grupos': grupos,
            'estado': estado_badge,
            'permisos': permisos_badges,
            'ultimo_login': ultimo_login,
            'acciones': acciones
        })
    
    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': data
    })


@login_required
@user_passes_test(is_admin_user)
@require_POST
def user_toggle_active(request, pk):
    """Vista AJAX para activar/desactivar un usuario"""
    user = get_object_or_404(User, pk=pk)
    
    # Prevenir que un usuario se desactive a sí mismo
    if user == request.user:
        return JsonResponse({
            'success': False,
            'message': 'No puedes desactivar tu propia cuenta.'
        }, status=400)
    
    # Cambiar estado
    user.is_active = not user.is_active
    user.save()
    
    estado_texto = 'activado' if user.is_active else 'desactivado'
    
    return JsonResponse({
        'success': True,
        'message': f'Usuario "{user.username}" {estado_texto} exitosamente.',
        'new_state': 'active' if user.is_active else 'inactive'
    })
