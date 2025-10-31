from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib.auth.models import Group

from ..forms import SignUpForm, CustomUserChangeForm, AsignarDirectorForm
from ..models import Maestro

@permission_required('gestion_escolar.acceder_ajustes', raise_exception=True)
def ajustes_view(request):
    return render(request, 'gestion_escolar/ajustes/ajustes.html', {'titulo': 'Ajustes'})

@login_required
def cambiar_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Tu contraseña ha sido actualizada correctamente.')
            return redirect('ajustes')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'gestion_escolar/ajustes/cambiar_password.html', {
        'form': form,
        'titulo': 'Cambiar Contraseña'
    })

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado correctamente.')
            return redirect('ajustes')
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, 'gestion_escolar/ajustes/editar_perfil.html', {'form': form, 'titulo': 'Editar Perfil'})

@user_passes_test(lambda u: u.is_superuser)
def asignar_director(request):
    if request.method == 'POST':
        form = AsignarDirectorForm(request.POST)
        if form.is_valid():
            maestro = form.cleaned_data['maestro']
            user = form.cleaned_data['usuario']
            
            maestro.user = user
            maestro.save()
            
            directores_group, created = Group.objects.get_or_create(name='Directores')
            user.groups.add(directores_group)
            
            messages.success(request, f'El maestro {maestro} ha sido asignado como director al usuario {user}.')
            return redirect('ajustes')
    else:
        form = AsignarDirectorForm()
    return render(request, 'gestion_escolar/ajustes/asignar_director.html', {'form': form, 'titulo': 'Asignar Director'})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"¡Bienvenido, {username}!")
                return redirect('index')
            else:
                messages.error(request, "Nombre de usuario o contraseña incorrectos.")
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = AuthenticationForm()
    
    context = {
        'form': form,
        'titulo': 'Iniciar Sesión'
    }
    return render(request, 'gestion_escolar/login.html', context)

def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('login')

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'¡Cuenta creada para {username}! Tu solicitud ha sido enviada para aprobación.')
            return redirect('login')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = SignUpForm()
    context = {
        'form': form,
        'titulo': 'Solicitud de Registro'
    }
    return render(request, 'gestion_escolar/signup.html', context)
