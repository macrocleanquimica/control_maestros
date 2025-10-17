from django import forms
from .models import (
    Zona, Escuela, Maestro, Categoria, MotivoTramite, 
    PlantillaTramite, Prelacion, TipoApreciacion, Vacancia, 
    Pendiente, Correspondencia, RegistroCorrespondencia
)
from django.contrib.auth.models import User, Group, Permission
import re

class PendienteForm(forms.ModelForm):
    class Meta:
        model = Pendiente
        fields = ['titulo', 'descripcion', 'fecha_programada']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fecha_programada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {
            'titulo': 'Título del Pendiente',
            'descripcion': 'Descripción (Opcional)',
            'fecha_programada': 'Fecha Programada',
        }

class RegistroCorrespondenciaForm(forms.ModelForm):
    class Meta:
        model = RegistroCorrespondencia
        fields = [
            'fecha_recibido', 'fecha_oficio', 'maestro', 'tipo_documento', 
            'folio_documento', 'remitente', 'contenido', 'area', 'observaciones',
            'archivo_adjunto', 'quien_recibio'
        ]
        widgets = {
            'fecha_recibido': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_oficio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'maestro': forms.Select(attrs={'class': 'form-control select2'}),
            'tipo_documento': forms.Select(attrs={'class': 'form-control'}),
            'folio_documento': forms.TextInput(attrs={'class': 'form-control', 'style': 'text-transform: uppercase;'}),
            'remitente': forms.TextInput(attrs={'class': 'form-control', 'style': 'text-transform: uppercase;'}),
            'contenido': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'style': 'text-transform: uppercase;'}),
            'area': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'style': 'text-transform: uppercase;'}),
            'archivo_adjunto': forms.FileInput(attrs={'class': 'form-control-file'}),
            'quien_recibio': forms.TextInput(attrs={'class': 'form-control', 'style': 'text-transform: uppercase;'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ['folio_documento', 'remitente', 'contenido', 'observaciones', 'quien_recibio']:
            if field_name in cleaned_data and cleaned_data[field_name]:
                cleaned_data[field_name] = cleaned_data[field_name].upper()
        return cleaned_data

class CorrespondenciaForm(forms.ModelForm):
    class Meta:
        model = Correspondencia
        fields = ['destinatario', 'asunto', 'cuerpo']
        widgets = {
            'destinatario': forms.Select(attrs={'class': 'form-control select2'}),
            'asunto': forms.TextInput(attrs={'class': 'form-control'}),
            'cuerpo': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
        }
        labels = {
            'destinatario': 'Para',
            'asunto': 'Asunto',
            'cuerpo': 'Mensaje',
        }

class VacanciaForm(forms.ModelForm):
    clave_presupuestal_display = forms.CharField(label="Clave Presupuestal", required=False, 
                                                 widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    curp_interino_display = forms.CharField(label="CURP Interino", required=False, 
                                            widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    folio_prelacion_display = forms.CharField(label="Folio de Prelación", required=False, 
                                              widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    posicion_orden_display = forms.CharField(label="Posición de Orden", required=False, 
                                             widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))

    class Meta:
        model = Vacancia
        fields = [
            'maestro_titular', 'maestro_interino', 'apreciacion', 'tipo_vacante', 'tipo_movimiento_original',
            'fecha_inicio', 'fecha_final', 'observaciones', 'pseudoplaza'
        ]
        widgets = {
            'maestro_titular': forms.Select(attrs={'class': 'form-control select2'}),
            'maestro_interino': forms.Select(attrs={'class': 'form-control select2'}),
            'apreciacion': forms.Select(attrs={'class': 'form-control select2'}),
            'tipo_vacante': forms.Select(attrs={'class': 'form-control'}),
            'tipo_movimiento_original': forms.Select(attrs={'class': 'form-control'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_final': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
            'pseudoplaza': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['maestro_titular'].queryset = Maestro.objects.all().order_by('a_paterno', 'a_materno', 'nombres')
        self.fields['maestro_interino'].queryset = Maestro.objects.all().order_by('a_paterno', 'a_materno', 'nombres')
        self.fields['maestro_interino'].required = False # Make interino optional
        for field_name, field in self.fields.items():
            if field_name not in ['maestro_titular', 'maestro_interino', 'apreciacion', 'tipo_vacante', 'tipo_movimiento_original']:
                field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        maestro = cleaned_data.get("maestro_titular")
        apreciacion = cleaned_data.get("apreciacion")

        if not maestro or not apreciacion:
            return cleaned_data

        categoria = maestro.categog.id_categoria if maestro.categog else ""
        apreciacion_desc = apreciacion.descripcion

        if apreciacion_desc == "ADMISIÓN.EDUCACIÓN BÁSICA.DOCENTE.EDUCACIÓN ESPECIAL.PSICOLOGÍA EDUCATIVA":
            if categoria not in ["E0689", "P04803"]:
                raise forms.ValidationError(
                    f"Para la apreciación '{apreciacion_desc}', la categoría del maestro ({categoria}) debe ser 'E0689' o 'P04803'."
                )

        validation_rules = {
            ("E0687", "E0281", "E0181", "E0681", "E0671"): "ADMISIÓN.EDUCACIÓN BÁSICA.DOCENTE.EDUCACIÓN ESPECIAL.EDUCACIÓN ESPECIAL",
            ("E0763", "E0761"): "ADMISIÓN.EDUCACIÓN BÁSICA.DOCENTE.EDUCACIÓN FÍSICA",
            ("E0629", "E0221"): "PROMOCIÓN. EDUCACIÓN BÁSICA. DIRECCIÓN. ESPECIAL. ESPECIAL. DIRECTOR DE ESCUELA DE EDUCACIÓN ESPECIAL",
            ("E0633",): "PROMOCIÓN. EDUCACIÓN BÁSICA. SUPERVISIÓN. ESPECIAL. ESPECIAL. SUPERVISOR DE EDUCACIÓN ESPECIAL. FORÁNEO",
            ("E0465", "E0461"): "ADMISIÓN.EDUCACIÓN BÁSICA.TÉCNICO DOCENTE.EDUCACIÓN ESPECIAL.MAESTRO DE TALLER",
        }

        for categorias_validas, apreciacion_esperada in validation_rules.items():
            if apreciacion_desc == apreciacion_esperada and categoria not in categorias_validas:
                raise forms.ValidationError(
                    f"Para la apreciación '{apreciacion_esperada}', la categoría del maestro ({categoria}) no corresponde. "
                    f"Debería ser una de las siguientes: {', '.join(categorias_validas)}"
                )

        return cleaned_data


class CategoriaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.id_categoria

class EscuelaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.id_escuela

class ZonaForm(forms.ModelForm):
    class Meta:
        model = Zona
        fields = '__all__'
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'numero': 'Número de Zona',
        }

class EscuelaForm(forms.ModelForm):
    class Meta:
        model = Escuela
        fields = '__all__'
        widgets = {
            'domicilio': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'id_escuela': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 10DML0013Q'}),
            'nombre_ct': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono_ct': forms.TextInput(attrs={'class': 'form-control'}),
            'region': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['zona_esc'].queryset = Zona.objects.all().order_by('numero')
        self.fields['zona_esc'].widget.attrs.update({'class': 'form-control'})
        self.fields['turno'].widget.attrs.update({'class': 'form-control'})
        self.fields['zona_economica'].widget.attrs.update({'class': 'form-control'})
        self.fields['u_d'].widget.attrs.update({'class': 'form-control'})
        self.fields['sostenimiento'].widget.attrs.update({'class': 'form-control'})

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = '__all__'
        widgets = {
            'id_categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
        }

class MaestroForm(forms.ModelForm):
    categog = CategoriaChoiceField(
        queryset=Categoria.objects.all().order_by('id_categoria'),
        required=False,
        label="Categoría",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    id_escuela = EscuelaChoiceField(
        queryset=Escuela.objects.all().order_by('id_escuela'),
        label="Escuela (CCT)",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )

    class Meta:
        model = Maestro
        exclude = ['id_maestro', 'fecha_registro', 'fecha_actualizacion', 'clave_presupuestal']
        widgets = {
            'domicilio_part': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_ingreso': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_promocion': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'a_paterno': forms.TextInput(attrs={'class': 'form-control'}),
            'a_materno': forms.TextInput(attrs={'class': 'form-control'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'curp': forms.TextInput(attrs={'class': 'form-control'}),
            'rfc': forms.TextInput(attrs={'class': 'form-control'}),
            'techo_f': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'form_academica': forms.TextInput(attrs={'class': 'form-control'}),
            'horario': forms.TextInput(attrs={'class': 'form-control'}),
            'funcion': forms.Select(attrs={'class': 'form-control'}),
            'poblacion': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'dep': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': '^\d{2}$',
                'title': '2 dígitos (ej: 07)',
                'placeholder': '00'
            }),
            'unid': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': '^\d{2}$',
                'title': '2 dígitos (ej: 10)',
                'placeholder': '00'
            }),
            'sub_unid': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': '^\d{2}$',
                'title': '2 dígitos (ej: 04)',
                'placeholder': '00'
            }),
            'hrs': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': '^\d{2}\.\d$',
                'title': 'Formato: XX.X (ej: 00.0, 42.0)',
                'placeholder': '00.0'
            }),
            'num_plaza': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': '^\d{6}$',
                'title': '6 dígitos (ej: 200314)',
                'placeholder': '000000'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['sexo'].widget.attrs.update({'class': 'form-control'})
        self.fields['est_civil'].widget.attrs.update({'class': 'form-control'})
        self.fields['nivel_estudio'].widget.attrs.update({'class': 'form-control'})
        self.fields['status'].widget.attrs.update({'class': 'form-control'})
        self.fields['funcion'].choices = Maestro.FUNCION_OPCIONES
        self.fields['dep'].widget.attrs.update({'class': 'form-control'})
        self.fields['unid'].widget.attrs.update({'class': 'form-control'})
        self.fields['sub_unid'].widget.attrs.update({'class': 'form-control'})
        self.fields['hrs'].widget.attrs.update({'class': 'form-control'})
        self.fields['num_plaza'].widget.attrs.update({'class': 'form-control'})

        if request and not request.user.is_superuser:
            if 'user' in self.fields:
                self.fields.pop('user')

    def clean_hrs(self):
        horas = self.cleaned_data.get('hrs')
        if horas:
            if not re.match(r'^\d{2}\.\d$', horas):
                raise forms.ValidationError('Formato de horas inválido. Debe ser: XX.X (ej: 01.0, 42.0)')
            parte_entera = int(horas.split('.')[0])
            if parte_entera < 0 or parte_entera > 42:
                raise forms.ValidationError('Las horas deben estar entre 00.0 y 42.0')
        return horas

    def clean(self):
        cleaned_data = super().clean()
        campos_clave = ['dep', 'unid', 'sub_unid', 'hrs', 'num_plaza']
        for campo in campos_clave:
            if campo not in cleaned_data:
                self.add_error(campo, 'Este campo es requerido para generar la clave presupuestal')
        return cleaned_data

class TramiteForm(forms.Form):
    def __init__(self, *args, **kwargs):
        form_type = kwargs.pop('form_type', None)
        super().__init__(*args, **kwargs)

        if form_type == 'oficios':
            self.fields['plantilla'].queryset = PlantillaTramite.objects.filter(
                tipo_documento='OFICIO'
            ).order_by('nombre')
        elif form_type == 'tramites':
            self.fields['plantilla'].queryset = PlantillaTramite.objects.filter(
                tipo_documento='TRAMITE'
            ).order_by('nombre')
        else:
            self.fields['plantilla'].queryset = PlantillaTramite.objects.all().order_by('nombre')

    plantilla = forms.ModelChoiceField(
        queryset=PlantillaTramite.objects.all().order_by('nombre'),
        label="Tipo de Trámite (Plantilla)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    motivo_tramite = forms.ModelChoiceField(
        queryset=MotivoTramite.objects.all().order_by('motivo_tramite'),
        label="Motivo del Movimiento",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    maestro_titular = forms.ModelChoiceField(
        queryset=Maestro.objects.all().order_by('a_paterno', 'a_materno', 'nombres'),
        label="Maestro Titular",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    maestro_interino = forms.ModelChoiceField(
        queryset=Maestro.objects.all().order_by('a_paterno', 'a_materno', 'nombres'),
        label="Maestro Interino (Opcional)",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    curp_titular_display = forms.CharField(label="CURP Titular", required=False,
                                           widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    rfc_titular_display = forms.CharField(label="RFC Titular", required=False,
                                          widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    clave_presupuestal_titular_display = forms.CharField(label="Clave Presupuestal Titular", required=False,
                                                         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    categoria_titular_display = forms.CharField(label="Categoría Titular", required=False,
                                                widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    funcion_titular_display = forms.CharField(label="Función Titular", required=False,
                                              widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    curp_interino_display = forms.CharField(label="CURP Interino", required=False,
                                            widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    rfc_interino_display = forms.CharField(label="RFC Interino", required=False,
                                           widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    clave_presupuestal_interino_display = forms.CharField(label="Clave Presupuestal Interino", required=False,
                                                          widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    funcion_interino_display = forms.CharField(label="Función Interino", required=False,
                                               widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    no_prel_display = forms.CharField(label="No. Prelación", required=False,
                                      widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    folio_prel_display = forms.CharField(label="Folio Prelación", required=False,
                                         widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    tipo_val_display = forms.CharField(label="Tipo de Valoración", required=False,
                                       widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    folio = forms.CharField(max_length=50, label="Folio", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    fecha_efecto1 = forms.DateField(label="Fecha inicial Titular", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    fecha_efecto2 = forms.DateField(label="Fecha Final Titular", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    fecha_efecto3 = forms.DateField(label="Fecha inicial Interino", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    fecha_efecto4 = forms.DateField(label="Fecha Final Interino", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    tipo_movimiento_interino = forms.CharField(max_length=100, label="Tipo de Movimiento Interino", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    observaciones = forms.CharField(label="Observaciones", required=False, widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))
    quincena_inicial = forms.CharField(
        max_length=6,
        label="Quincena de Inicio (YYYYQQ)",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'pattern': '^\d{6}',
            'title': 'Formato: YYYYQQ (ej: 202501)'
        })
    )
    quincena_final = forms.CharField(
        max_length=6,
        label="Quincena Final (YYYYQQ)",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'pattern': '^\d{6}$',
            'title': 'Formato: YYYYQQ (ej: 202524)'
        })
    )

from django.contrib.auth.forms import UserCreationForm, UserChangeForm

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, label='Nombre(s)')
    last_name = forms.CharField(max_length=150, required=True, label='Apellidos')
    email = forms.EmailField(max_length=254, required=True, label='Correo electrónico')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False
        if commit:
            user.save()
        return user

class CustomUserChangeForm(UserChangeForm):
    password = None
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

class AsignarDirectorForm(forms.Form):
    maestro = forms.ModelChoiceField(
        queryset=Maestro.objects.filter(user__isnull=True),
        label="Maestro"
    )
    usuario = forms.ModelChoiceField(
        queryset=User.objects.filter(maestro_profile__isnull=True, is_superuser=False),
        label="Usuario"
    )

from .models import DocumentoExpediente

class DocumentoExpedienteForm(forms.ModelForm):
    class Meta:
        model = DocumentoExpediente
        fields = ['tipo_documento', 'archivo']
        widgets = {
            'tipo_documento': forms.Select(attrs={'class': 'form-control'}),
            'archivo': forms.FileInput(attrs={'class': 'form-control-file'}),
        }


class RolePermissionForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Nombre del Rol',
        }

    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.filter(content_type__app_label='gestion_escolar'),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(RolePermissionForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['permissions'].initial = self.instance.permissions.all()

    def save(self, *args, **kwargs):
        group = super(RolePermissionForm, self).save(commit=False)
        group.save()
        group.permissions.set(self.cleaned_data['permissions'])
        return group
