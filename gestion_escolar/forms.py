from django import forms
from .models import (
    Zona, Escuela, Maestro, Categoria, MotivoTramite, Tema,
    PlantillaTramite, Prelacion, TipoApreciacion, Vacancia, 
    Pendiente, Correspondencia, RegistroCorrespondencia, FUP
)
from django.contrib.auth.models import User, Group, Permission
import re

class UppercaseFormMixin(object):
    """
    Mixin para convertir a mayúsculas los campos de texto de un formulario.
    Aplica un estilo CSS y un script oninput para que el texto se vea en mayúsculas 
    mientras se escribe y convierte el valor a mayúsculas antes de validarlo.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        no_upper = getattr(self, 'no_upper_fields', ())
        for field_name, field in self.fields.items():
            if field_name in no_upper:
                continue
            if isinstance(field, forms.CharField) and not isinstance(field, forms.EmailField):
                if isinstance(field.widget, (forms.TextInput, forms.Textarea)):
                    field.widget.attrs.update({
                        'style': 'text-transform: uppercase;',
                        'oninput': 'this.value = this.value.toUpperCase()'
                    })

    def clean(self):
        cleaned_data = super().clean()
        no_upper = getattr(self, 'no_upper_fields', ())
        for field_name, value in cleaned_data.items():
            if field_name in no_upper:
                continue
            field = self.fields.get(field_name)
            if isinstance(value, str) and field and not isinstance(field, forms.EmailField):
                cleaned_data[field_name] = value.upper()
        return cleaned_data

class PendienteForm(UppercaseFormMixin, forms.ModelForm):
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

class RegistroCorrespondenciaForm(UppercaseFormMixin, forms.ModelForm):
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
            'folio_documento': forms.TextInput(attrs={'class': 'form-control'}),
            'remitente': forms.TextInput(attrs={'class': 'form-control'}),
            'contenido': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'area': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'archivo_adjunto': forms.FileInput(attrs={'class': 'form-control-file'}),
            'quien_recibio': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CorrespondenciaForm(UppercaseFormMixin, forms.ModelForm):
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

class VacanciaForm(UppercaseFormMixin, forms.ModelForm):
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
            'maestro_titular', 'maestro_interino', 'apreciacion', 'tipo_vacante', 'plantilla_doc', 'tipo_movimiento_original',
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
        self.fields['fecha_final'].required = False
        self.fields['tipo_movimiento_original'].required = False

        # Solo lectura: no crear catálogos desde el formulario.
        # El TipoApreciacion de promoción debe existir por datos/migración;
        # aquí solo se ordena el queryset sin efectos secundarios.
        self.fields['apreciacion'].queryset = TipoApreciacion.objects.all().order_by('descripcion')

        for field_name, field in self.fields.items():
            if field_name not in ['maestro_titular', 'maestro_interino', 'apreciacion', 'tipo_vacante', 'tipo_movimiento_original']:
                field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        maestro = cleaned_data.get("maestro_titular")
        apreciacion = cleaned_data.get("apreciacion")
        tipo_vacante = cleaned_data.get("tipo_vacante")

        if not maestro:
            return cleaned_data

        categoria = maestro.categog.id_categoria if maestro.categog else ""

        if not apreciacion:
            # Si la apreciación no se asignó automáticamente y no se proveyó, es un error.
            self.add_error('apreciacion', 'Este campo es requerido.')
            return cleaned_data

        apreciacion_desc = apreciacion.descripcion

        # Si la vacante es definitiva, la fecha final no es requerida y debe ser nula.
        if tipo_vacante == 'DEFINITIVA':
            cleaned_data['fecha_final'] = None
            cleaned_data['tipo_movimiento_original'] = None
        elif not cleaned_data.get('fecha_final'):
            # Si es temporal, la fecha final es obligatoria.
            self.add_error('fecha_final', 'Este campo es requerido para vacantes temporales.')

        if apreciacion_desc == "ADMISIÓN.EDUCACIÓN BÁSICA.DOCENTE.EDUCACIÓN ESPECIAL.PSICOLOGÍA EDUCATIVA":
            funcion = (maestro.funcion or '').upper().replace('Ó', 'O')
            es_psicologo = 'PSICOLOG' in funcion
            if not es_psicologo and categoria not in ["E0689", "P04803"]:
                raise forms.ValidationError(
                    f"Para la apreciación '{apreciacion_desc}', la categoría del maestro ({categoria}) debe ser 'E0689' o 'P04803'."
                )

        validation_rules = {
            ("E0687", "E0281", "E0181", "E0681", "E0671"): "ADMISIÓN.EDUCACIÓN BÁSICA.DOCENTE.EDUCACIÓN ESPECIAL.EDUCACIÓN ESPECIAL",
            ("E0763", "E0761"): "ADMISIÓN.EDUCACIÓN BÁSICA.DOCENTE.EDUCACIÓN FÍSICA",
            ("E0629", "E0221"): "PROMOCIÓN.EDUCACIÓN BÁSICA.DIRECCIÓN.ESPECIAL.ESPECIAL.DIRECTOR DE ESCUELA DE EDUCACIÓN ESPECIAL",
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
        return f"{obj.nombre_ct} ({obj.id_escuela})"

class ClaveChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.id_escuela

class ZonaForm(UppercaseFormMixin, forms.ModelForm):
    no_upper_fields = ('nombre',)

    class Meta:
        model = Zona
        fields = '__all__'
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'numero': 'Número de Zona',
            'nombre': 'Nombre de la zona (opcional)',
        }

class EscuelaForm(UppercaseFormMixin, forms.ModelForm):
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

class CategoriaForm(UppercaseFormMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = '__all__'
        widgets = {
            'id_categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
        }

class MaestroForm(UppercaseFormMixin, forms.ModelForm):
    categog = CategoriaChoiceField(
        queryset=Categoria.objects.all().order_by('id_categoria'),
        required=False,
        label="Categoría",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    id_escuela = EscuelaChoiceField(
        queryset=Escuela.objects.all().order_by('id_escuela'),
        label="Escuela de Adscripción (CCT)",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2-escuelas', 'style': 'width: 100%;'})
    )
    
    techo_f = ClaveChoiceField(
        queryset=Escuela.objects.all().order_by('id_escuela'),
        label="CCT del Techo Financiero",
        required=False,
        to_field_name='id_escuela',
        widget=forms.Select(attrs={'class': 'form-control select2-escuelas', 'style': 'width: 100%;'})
    )

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # Cargamos el catálogo completo para estabilidad (solo 127 registros)
        self.fields['id_escuela'].queryset = Escuela.objects.all().order_by('nombre_ct')
        self.fields['techo_f'].queryset = Escuela.objects.all().order_by('id_escuela')
        
        # Configuración de otros campos
        self.fields['maestro_principal'].queryset = Maestro.objects.all().order_by('a_paterno', 'a_materno', 'nombres')
        self.fields['maestro_principal'].widget.attrs.update({'class': 'form-control select2'})
        
        self.fields['sexo'].widget.attrs.update({'class': 'form-control'})
        self.fields['est_civil'].widget.attrs.update({'class': 'form-control'})
        self.fields['nivel_estudio'].widget.attrs.update({'class': 'form-control'})
        self.fields['status'].widget.attrs.update({'class': 'form-control'})
        
        if request and not request.user.is_superuser:
            if 'user' in self.fields:
                self.fields.pop('user')

    def clean(self):
        cleaned_data = super().clean()
        a_paterno = cleaned_data.get('a_paterno')
        a_materno = cleaned_data.get('a_materno')
        nombres = cleaned_data.get('nombres')
        curp = cleaned_data.get('curp')
        rfc = cleaned_data.get('rfc')
        id_escuela = cleaned_data.get('id_escuela')

        if all(v is not None for v in [a_paterno, a_materno, nombres, curp, rfc]) and id_escuela:
            qs = Maestro.objects.filter(
                a_paterno=a_paterno, a_materno=a_materno, nombres=nombres,
                curp=curp, rfc=rfc, id_escuela=id_escuela,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    'Ya existe un maestro registrado con esos mismos datos '
                    '(nombre, CURP, RFC, escuela, clave presupuestal). '
                    'Verifique antes de crear un duplicado.'
                )

        # Validar formato de campos de clave solo si se capturaron
        # (el modelo los permite en blanco, asi que no se fuerzan como obligatorios).
        import re as _re
        formatos = [
            ('dep', r'^\d{2}$', 'Dependencia debe tener 2 dígitos'),
            ('unid', r'^\d{2}$', 'Unidad debe tener 2 dígitos'),
            ('sub_unid', r'^\d{2}$', 'Subunidad debe tener 2 dígitos'),
            ('hrs', r'^\d{2}\.\d$', 'Horas deben tener formato XX.X'),
            ('num_plaza', r'^\d{6}$', 'Número de plaza debe tener 6 dígitos'),
        ]
        for campo, patron, mensaje in formatos:
            valor = cleaned_data.get(campo)
            if valor and not _re.match(patron, str(valor)):
                self.add_error(campo, mensaje)
        return cleaned_data

    def clean_techo_f(self):
        techo = self.cleaned_data.get('techo_f')
        # Si es un objeto Escuela (porque usamos ModelChoiceField), devolvemos solo la clave string
        if techo and hasattr(techo, 'id_escuela'):
            return techo.id_escuela
        return techo

    class Meta:
        model = Maestro
        exclude = ['id_maestro', 'fecha_registro', 'fecha_actualizacion', 'clave_presupuestal', 'incentivo']
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
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'form_academica': forms.TextInput(attrs={'class': 'form-control'}),
            'horario': forms.TextInput(attrs={'class': 'form-control'}),
            'funcion': forms.Select(attrs={'class': 'form-control'}),
            'poblacion': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'incentivos': forms.SelectMultiple(attrs={'class': 'form-control select2', 'multiple': 'multiple'}),
            'dep': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': r'^\d{2}$',
                'title': '2 dígitos (ej: 07)',
                'placeholder': '00'
            }),
            'unid': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': r'^\d{2}$',
                'title': '2 dígitos (ej: 10)',
                'placeholder': '00'
            }),
            'sub_unid': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': r'^\d{2}$',
                'title': '2 dígitos (ej: 04)',
                'placeholder': '00'
            }),
            'hrs': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': r'^\d{2}\.\d$',
                'title': 'Formato: XX.X (ej: 00.0, 42.0)',
                'placeholder': '00.0'
            }),
            'num_plaza': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': r'^\d{6}$',
                'title': '6 dígitos (ej: 200314)',
                'placeholder': '000000'
            }),
        }

    def clean_hrs(self):
        horas = self.cleaned_data.get('hrs')
        if horas:
            if not re.match(r'^\d{2}\.\d$', horas):
                raise forms.ValidationError('Formato de horas inválido. Debe ser: XX.X (ej: 01.0, 42.0)')
            parte_entera = int(horas.split('.')[0])
            if parte_entera < 0 or parte_entera > 42:
                raise forms.ValidationError('Las horas deben estar entre 00.0 y 42.0')
        return horas

class TramiteForm(UppercaseFormMixin, forms.Form):
    archivo_plantilla_especifico = forms.ChoiceField(
        choices=[
            ('', '--- Seleccione una variante de plantilla ---'),
            ('SOLICITUDASIGNACION.docx', 'SOLICITUD DE ASIGNACION (Art. 3)'),
            ('SOLICITUDASIGNACION36.docx', 'SOLICITUD DE ASIGNACION (Art. 36)'),
        ],
        label="Variante de Plantilla (.docx)",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    def __init__(self, *args, **kwargs):
        form_type = kwargs.pop('form_type', None)
        super().__init__(*args, **kwargs)

        if form_type == 'oficios':
            self.fields['plantilla'].queryset = PlantillaTramite.objects.filter(
                tipo_documento='OFICIO'
            ).exclude(nombre__icontains="36").order_by('nombre')
        elif form_type == 'tramites':
            self.fields['plantilla'].queryset = PlantillaTramite.objects.filter(
                tipo_documento='TRAMITE'
            ).exclude(nombre__icontains="36").order_by('nombre')
        else:
            self.fields['plantilla'].queryset = PlantillaTramite.objects.all().exclude(nombre__icontains="36").order_by('nombre')

    tipo_cambio = forms.ChoiceField(
        choices=[('', '--- Seleccione ---'), ('sustitucion', 'Sustitución'), ('incremento', 'Incremento')],
        label="Tipo de Cambio",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    maestro_sustituido = forms.ModelChoiceField(
        queryset=Maestro.objects.all().order_by('a_paterno', 'a_materno', 'nombres'),
        label="Maestro Sustituido",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    escuela_destino = forms.ModelChoiceField(
        queryset=Escuela.objects.all().order_by('nombre_ct'),
        to_field_name='id_escuela',
        label="Centro de Trabajo Destino",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    plantilla = forms.ModelChoiceField(
        queryset=PlantillaTramite.objects.all().order_by('nombre'),
        label="Tipo de Trámite (Plantilla)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    motivo_tramite = forms.ModelChoiceField(
        queryset=MotivoTramite.objects.all().order_by('motivo_tramite'),
        label="Motivo del Movimiento",
        required=False, # Added this line
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
    nombre_titular_display = forms.CharField(label="Nombre Completo Titular", required=False,
                                            widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
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
    form_academica_titular_display = forms.CharField(label="Formación Académica Titular", required=False,
                                                    widget=forms.TextInput(attrs={'class': 'form-control'}))
    ze_techo_f_display = forms.CharField(label="Zona Económica (Techo F.)", required=False,
                                         widget=forms.TextInput(attrs={'class': 'form-control'}))
    nombre_interino_display = forms.CharField(label="Nombre Completo Interino", required=False,
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
    folio = forms.CharField(max_length=50, label="Folio de Oficio (Manual)", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Capture el folio del control de oficios'}))
    fecha_efecto1 = forms.DateField(label="Fecha inicial Titular", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'))
    fecha_efecto2 = forms.DateField(label="Fecha Final Titular", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'))
    fecha_efecto3 = forms.DateField(label="Fecha inicial Interino", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'))
    fecha_efecto4 = forms.DateField(label="Fecha Final Interino", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'))
    tipo_movimiento_interino = forms.CharField(max_length=100, label="Tipo de Movimiento Interino", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    observaciones = forms.CharField(label="Observaciones", required=False, widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}))
    quincena_inicial = forms.CharField(
        max_length=6,
        label="Quincena de Inicio (YYYYQQ)",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'pattern': r'^\d{6}',
            'title': 'Formato: YYYYQQ (ej: 202501)'
        })
    )
    quincena_final = forms.CharField(
        max_length=6,
        label="Quincena Final (YYYYQQ)",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'pattern': r'^\d{6}$',
            'title': 'Formato: YYYYQQ (ej: 202524)'
        })
    )
    # Campos para "Constancia de Cambio"
    fecha_al_corte = forms.DateField(
        label="Fecha al Corte",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d')
    )
    fecha_del_calculo = forms.DateField(
        label="Fecha del Cálculo",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d')
    )
    antiguedad_funcion = forms.CharField(
        max_length=100,
        label="Antigüedad en la Función",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    antiguedad_categoria = forms.CharField(
        max_length=100,
        label="Antigüedad en la Categoría",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    fecha_del_calculo_servicio = forms.DateField(
        label="Fecha Ingreso al Servicio",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d')
    )
    antiguedad_servicio = forms.CharField(
        max_length=100,
        label="Antigüedad en el Servicio",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    fecha_adscripcion = forms.DateField(
        label="Fecha de Adscripción",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d')
    )
    incentivos = forms.CharField(
        max_length=255,
        label="Incentivos",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

from django.contrib.auth.forms import UserCreationForm, UserChangeForm

class SignUpForm(UppercaseFormMixin, UserCreationForm):
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

class CustomUserChangeForm(UppercaseFormMixin, UserChangeForm):
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


class RolePermissionForm(UppercaseFormMixin, forms.ModelForm):
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

class TemaForm(UppercaseFormMixin, forms.ModelForm):
    class Meta:
        model = Tema
        fields = ['nombre', 'activo', 'fecha_inicio', 'fecha_fin', 'color_principal', 'color_secundario', 'color_texto', 'color_dropdown', 'imagen_fondo', 'usar_filtro_oscuro']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'usar_filtro_oscuro': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'imagen_fondo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('fecha_inicio') and cleaned_data.get('fecha_fin') and cleaned_data['fecha_fin'] < cleaned_data['fecha_inicio']:
            raise forms.ValidationError("La fecha de fin no puede ser anterior a la fecha de inicio.")
        return cleaned_data

class FUPForm(UppercaseFormMixin, forms.ModelForm):
    class Meta:
        model = FUP
        fields = ['maestro', 'techo_financiero', 'efectos', 'folio', 'observaciones', 'sostenimiento', 'archivo']
        widgets = {
            'maestro': forms.Select(attrs={'class': 'form-control select2'}),
            'techo_financiero': forms.TextInput(attrs={'class': 'form-control'}),
            'efectos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ejemplo: 202509-202515 o 202515-999999 (definitivo)',
                'pattern': r'\d{6}-(\d{6}|999999)',
                'title': 'Formato: AAAAMM-AAAAMM (Ejemplo: 202509-202515) o AAAAMM-999999 para maestros definitivos'
            }),
            'folio': forms.TextInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'sostenimiento': forms.Select(attrs={'class': 'form-control'}),
            'archivo': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Hacer campos obligatorios y agregar mensajes personalizados
        campos_obligatorios = {
            'maestro': 'El nombre del maestro es obligatorio.',
            'folio': 'El folio es obligatorio.',
            'sostenimiento': 'El sostenimiento es obligatorio.',
            'efectos': 'Los efectos son obligatorios.'
        }
        
        for campo, mensaje in campos_obligatorios.items():
            self.fields[campo].required = True
            self.fields[campo].error_messages = {
                'required': mensaje
            }

    def clean_folio(self):
        folio = self.cleaned_data.get('folio')
        if folio:
            # Buscar si ya existe un FUP con este folio
            # Excluir el registro actual si estamos editando (self.instance.pk)
            existe = FUP.objects.filter(folio=folio).exclude(pk=self.instance.pk).exists()
            
            if existe:
                raise forms.ValidationError('Este folio ya ha sido registrado anteriormente.')
        return folio

    def clean_efectos(self):
        import re
        efectos = self.cleaned_data.get('efectos')
        
        if efectos:
            # Validar formato AAAAMM-AAAAMM (6 dígitos - 6 dígitos) o AAAAMM-999999 para maestros definitivos
            pattern = r'^\d{6}-(\d{6}|999999)$'
            if not re.match(pattern, efectos):
                raise forms.ValidationError(
                    'El formato debe ser AAAAMM-AAAAMM (Ejemplo: 202509-202515) o AAAAMM-999999 para maestros definitivos'
                )
            
            # Validar que las partes sean válidas
            partes = efectos.split('-')
            inicio = partes[0]
            fin = partes[1]
            
            # Validar año (primeros 4 dígitos) del inicio
            año_inicio = int(inicio[:4])
            
            if año_inicio < 2000 or año_inicio > 2100:
                raise forms.ValidationError('El año de inicio debe estar entre 2000 y 2100')
            
            # Validar quincena de inicio (últimos 2 dígitos: 01-24)
            quincena_inicio = int(inicio[4:6])
            
            if quincena_inicio < 1 or quincena_inicio > 24:
                raise forms.ValidationError('La quincena de inicio debe estar entre 01 y 24')
            
            # Si la fecha de fin es 999999, es un maestro definitivo (sin fecha de término)
            if fin == '999999':
                # No validar más, es válido para maestros definitivos
                pass
            else:
                # Validar fecha de fin normal
                año_fin = int(fin[:4])
                quincena_fin = int(fin[4:6])
                
                if año_fin < 2000 or año_fin > 2100:
                    raise forms.ValidationError('El año de fin debe estar entre 2000 y 2100')
                
                if quincena_fin < 1 or quincena_fin > 24:
                    raise forms.ValidationError('La quincena de fin debe estar entre 01 y 24')
                
                # Validar que el periodo de fin sea mayor o igual al de inicio
                if int(fin) < int(inicio):
                    raise forms.ValidationError('El periodo de fin debe ser mayor o igual al de inicio')
        
        return efectos