from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from .models import Maestro


class UserCreationFormCustom(UserCreationForm):
    """Formulario personalizado para crear usuarios con campos adicionales"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label='Nombre(s)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre(s)'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label='Apellidos',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'})
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label='Grupos/Roles',
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2', 'multiple': 'multiple'})
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label='Usuario Activo',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    is_staff = forms.BooleanField(
        required=False,
        initial=False,
        label='Acceso al Panel de Administración',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    is_superuser = forms.BooleanField(
        required=False,
        initial=False,
        label='Superusuario (todos los permisos)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    maestro = forms.ModelChoiceField(
        queryset=Maestro.objects.all(),
        required=False,
        label='Vincular con Maestro (Opcional)',
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        help_text='Si este usuario corresponde a un maestro registrado, selecciónalo aquí'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 
                  'groups', 'is_active', 'is_staff', 'is_superuser', 'maestro')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Contraseña'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirmar contraseña'})
        
        # Personalizar labels
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Confirmar Contraseña'
        self.fields['username'].label = 'Nombre de Usuario'
        self.fields['email'].label = 'Correo Electrónico'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Ya existe un usuario con este correo electrónico.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_active = self.cleaned_data['is_active']
        user.is_staff = self.cleaned_data['is_staff']
        user.is_superuser = self.cleaned_data['is_superuser']
        
        if commit:
            user.save()
            # Asignar grupos
            user.groups.set(self.cleaned_data['groups'])
            
            # Vincular con maestro si se seleccionó
            maestro = self.cleaned_data.get('maestro')
            if maestro:
                maestro.user = user
                maestro.save()
        
        return user


class UserUpdateFormCustom(forms.ModelForm):
    """Formulario personalizado para editar usuarios existentes"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label='Nombre(s)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre(s)'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label='Apellidos',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'})
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label='Grupos/Roles',
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2', 'multiple': 'multiple'})
    )
    is_active = forms.BooleanField(
        required=False,
        label='Usuario Activo',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    is_staff = forms.BooleanField(
        required=False,
        label='Acceso al Panel de Administración',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    is_superuser = forms.BooleanField(
        required=False,
        label='Superusuario (todos los permisos)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    maestro = forms.ModelChoiceField(
        queryset=Maestro.objects.all(),
        required=False,
        label='Vincular con Maestro (Opcional)',
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        help_text='Si este usuario corresponde a un maestro registrado, selecciónalo aquí'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'groups', 
                  'is_active', 'is_staff', 'is_superuser', 'maestro')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalizar labels
        self.fields['username'].label = 'Nombre de Usuario'
        self.fields['email'].label = 'Correo Electrónico'
        
        # Cargar el maestro vinculado si existe
        if self.instance and self.instance.pk:
            try:
                maestro = Maestro.objects.get(user=self.instance)
                self.fields['maestro'].initial = maestro
            except Maestro.DoesNotExist:
                pass

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Verificar que el email no esté en uso por otro usuario
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Ya existe un usuario con este correo electrónico.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            # Asignar grupos
            user.groups.set(self.cleaned_data['groups'])
            
            # Desvincular maestro anterior si existía
            Maestro.objects.filter(user=user).update(user=None)
            
            # Vincular con nuevo maestro si se seleccionó
            maestro = self.cleaned_data.get('maestro')
            if maestro:
                # Desvincular el maestro de cualquier otro usuario
                if maestro.user and maestro.user != user:
                    maestro.user = None
                maestro.user = user
                maestro.save()
        
        return user


class AdminPasswordChangeForm(forms.Form):
    """Formulario para que un administrador cambie la contraseña de un usuario"""
    
    password1 = forms.CharField(
        label='Nueva Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nueva contraseña'}),
        help_text='Mínimo 8 caracteres'
    )
    password2 = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError('Las contraseñas no coinciden.')
        
        return password2

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        
        if len(password1) < 8:
            raise ValidationError('La contraseña debe tener al menos 8 caracteres.')
        
        return password1

    def save(self, commit=True):
        password = self.cleaned_data['password1']
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user
