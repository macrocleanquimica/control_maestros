from django import forms
from django.db.models import Q
from .models import (
    Zona, Escuela, Maestro, Categoria, MotivoTramite, Tema,
    PlantillaTramite, Prelacion, TipoApreciacion, Vacancia, 
    Pendiente, Correspondencia, RegistroCorrespondencia, FUP
)
from django.contrib.auth.models import User, Group, Permission
import re

from .validators import (
    es_curp_valida,
    es_rfc_valido,
    normalizar_curp,
    normalizar_rfc,
    validar_curp,
    validar_rfc,
)

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
            'fecha_programada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
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
            'fecha_recibido': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'fecha_oficio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
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
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'fecha_final': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
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

        # Si la vacante es definitiva, la fecha final es opcional: se conserva
        # la fecha tecleada si existe, y solo queda en blanco si no se capturó.
        if tipo_vacante == 'DEFINITIVA':
            cleaned_data['tipo_movimiento_original'] = None
        elif not cleaned_data.get('fecha_final'):
            # Si es temporal, la fecha final es obligatoria.
            self.add_error('fecha_final', 'Este campo es requerido para vacantes temporales.')

        # La fecha inicial no puede ser mayor a la final; final vacía = sin fin.
        fi = cleaned_data.get('fecha_inicio')
        ff = cleaned_data.get('fecha_final')
        if fi and ff and fi > ff:
            self.add_error(
                'fecha_final',
                'La fecha inicial no puede ser mayor a la fecha final. '
                'Deje la fecha final vacía si no tiene fin.'
            )

        if apreciacion_desc == "ADMISIÓN.EDUCACIÓN BÁSICA.DOCENTE.EDUCACIÓN ESPECIAL.PSICOLOGÍA EDUCATIVA":
            funcion = (maestro.funcion or '').upper().replace('Ó', 'O')
            es_psicologo = 'PSICOLOG' in funcion
            if not es_psicologo and categoria not in ["E0689", "E0671", "P04803"]:
                raise forms.ValidationError(
                    f"Para la apreciación '{apreciacion_desc}', la categoría del maestro ({categoria}) debe ser 'E0689', 'E0671' o 'P04803'."
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
            'horas': forms.TextInput(attrs={'class': 'form-control'}),
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
        # En "agregar otra plaza" se comparte CURP a propósito (misma persona,
        # clave nueva): ahí el candado no aplica.
        self.permitir_curp_duplicada = kwargs.pop('permitir_curp_duplicada', False)
        # La validación de CURP/RFC solo se activa en alta, edición y "agregar
        # otra plaza" (no en admin ni en otros formularios que reutilicen esta
        # clase).
        self.validar_curp_rfc = kwargs.pop('validar_curp_rfc', False)
        # Valores heredados de un registro existente (usado por "agregar otra
        # plaza"). Si la CURP/RFC vieja es inválida y no se modifica, se permite
        # guardar y solo se advierte.
        legacy_curp = kwargs.pop('legacy_curp', None)
        legacy_rfc = kwargs.pop('legacy_rfc', None)
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

        if self.instance and self.instance.pk:
            self._curp_guardada = normalizar_curp(self.instance.curp)
            self._rfc_guardado = normalizar_rfc(self.instance.rfc)
        else:
            self._curp_guardada = normalizar_curp(legacy_curp)
            self._rfc_guardado = normalizar_rfc(legacy_rfc)
        # Avisos para datos heredados que no pasan la validación actual. Se
        # recalculan en clean_curp/clean_rfc si el usuario corrige el valor.
        self.curp_aviso_legacy = bool(self._curp_guardada) and not es_curp_valida(self._curp_guardada)
        self.rfc_aviso_legacy = bool(self._rfc_guardado) and not es_rfc_valido(self._rfc_guardado)

        if request and not request.user.is_superuser:
            if 'user' in self.fields:
                self.fields.pop('user')

    def clean_curp(self):
        valor = normalizar_curp(self.cleaned_data.get('curp'))
        self.curp_aviso_legacy = False
        if not valor:
            return ''
        if not self.validar_curp_rfc:
            return valor
        # Dato viejo sin cambios: se conserva tal cual y solo se advierte.
        if valor == self._curp_guardada:
            if not es_curp_valida(valor):
                self.curp_aviso_legacy = True
            return valor
        validar_curp(valor)
        return valor

    def clean_rfc(self):
        valor = normalizar_rfc(self.cleaned_data.get('rfc'))
        self.rfc_aviso_legacy = False
        if not valor:
            return ''
        if not self.validar_curp_rfc:
            return valor
        # Dato viejo sin cambios: se conserva tal cual y solo se advierte.
        if valor == self._rfc_guardado:
            if not es_rfc_valido(valor):
                self.rfc_aviso_legacy = True
            return valor
        validar_rfc(valor)
        return valor

    def clean(self):
        cleaned_data = super().clean()
        a_paterno = cleaned_data.get('a_paterno')
        a_materno = cleaned_data.get('a_materno')
        nombres = cleaned_data.get('nombres')
        curp = cleaned_data.get('curp')
        rfc = cleaned_data.get('rfc')
        id_escuela = cleaned_data.get('id_escuela')
        num_plaza = cleaned_data.get('num_plaza')

        # El duplicado es la COMBINACION persona + escuela + plaza. Sin el numero
        # de plaza, todo maestro con varias plazas (77 personas / 193 filas) se
        # marcaba como duplicado de si mismo, y ni siquiera se podia editar.
        if all(v is not None for v in [a_paterno, a_materno, nombres, curp, rfc]) and id_escuela:
            qs = Maestro.objects.filter(
                a_paterno=a_paterno, a_materno=a_materno, nombres=nombres,
                curp=curp, rfc=rfc, id_escuela=id_escuela,
                num_plaza=num_plaza,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    'Ya existe otro maestro con esos mismos datos '
                    '(nombre, CURP, RFC, escuela y número de plaza). '
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

        # Candado CURP exacta: si ya existe otro registro con la misma CURP, el
        # trabajador ya está registrado. No se crea persona nueva: la clave debe
        # agregarse como otra plaza desde su Detalle. Aplica en alta, edición y
        # admin (ver MaestroAdmin); "agregar otra plaza" lo desactiva a propósito.
        if not self.permitir_curp_duplicada:
            curp_val = (curp or '').strip()
            if curp_val:
                qs_curp = Maestro.objects.filter(curp__iexact=curp_val)
                if self.instance.pk:
                    # Excluir a toda la persona (raíz + plazas secundarias): la
                    # misma CURP en sus otras plazas no es duplicado.
                    raiz = self.instance
                    vistos = set()
                    while getattr(raiz, 'maestro_principal_id', None):
                        if raiz.maestro_principal_id in vistos:
                            break
                        vistos.add(raiz.maestro_principal_id)
                        padre = Maestro.objects.filter(pk=raiz.maestro_principal_id).first()
                        if not padre:
                            break
                        raiz = padre
                    propios = {raiz.pk} | set(
                        Maestro.objects.filter(maestro_principal_id=raiz.pk).values_list('pk', flat=True)
                    )
                    qs_curp = qs_curp.exclude(pk__in=propios)
                duplicado = qs_curp.first()
                if duplicado:
                    cct_dup = duplicado.id_escuela.id_escuela if duplicado.id_escuela else 's/CCT'
                    self.add_error(
                        'curp',
                        f'Esta CURP ya existe: {duplicado.nombres or ""} {duplicado.a_paterno or ""} '
                        f'{duplicado.a_materno or ""} (ID {duplicado.id_maestro}, CCT {cct_dup}). '
                        'El maestro ya está registrado: agréguele la clave presupuestal como '
                        'otra plaza desde su Detalle, no lo cree de nuevo.'
                    )
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
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'fecha_ingreso': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'fecha_promocion': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'a_paterno': forms.TextInput(attrs={'class': 'form-control'}),
            'a_materno': forms.TextInput(attrs={'class': 'form-control'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'curp': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '18',
                'autocomplete': 'off',
                'spellcheck': 'false',
                'placeholder': '18 caracteres',
            }),
            'rfc': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '13',
                'autocomplete': 'off',
                'spellcheck': 'false',
                'placeholder': '13 caracteres',
            }),
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
        plantilla_id = kwargs.pop('plantilla_id', None)
        super().__init__(*args, **kwargs)

        # La plantilla puede venir del POST, del initial o de la URL (?plantilla=).
        if plantilla_id is None:
            if self.is_bound:
                plantilla_id = self.data.get('plantilla')
            else:
                plantilla_id = self.initial.get('plantilla')
        plantilla_id = self._normalizar_pk(plantilla_id)

        queryset = PlantillaTramite.objects.all()
        if form_type == 'oficios':
            queryset = queryset.filter(tipo_documento='OFICIO')
        elif form_type == 'tramites':
            queryset = queryset.filter(tipo_documento='TRAMITE')
        queryset = queryset.exclude(nombre__icontains="36")
        # Las plantillas desactivadas no se ofrecen, salvo que sea la que se
        # está corrigiendo (para no romper un historial viejo).
        if plantilla_id:
            queryset = queryset.filter(Q(activa=True) | Q(pk=plantilla_id))
        else:
            queryset = queryset.filter(activa=True)
        self.fields['plantilla'].queryset = queryset.order_by('nombre')

        self.plantilla_id = plantilla_id
        self.plantilla_seleccionada = None
        if plantilla_id:
            self.plantilla_seleccionada = PlantillaTramite.objects.filter(pk=plantilla_id).first()

        from .campos_plantilla import (
            CAMPOS_SOLO_LECTURA, CATALOGO_CAMPOS, config_de_plantilla,
            nombre_campo_personalizado,
        )
        self.configuracion_plantilla = config_de_plantilla(self.plantilla_seleccionada)
        self.campos_visibles = set(self.configuracion_plantilla.get('campos') or [])
        self.campos_requeridos = set(self.configuracion_plantilla.get('requeridos') or [])

        # El formulario conserva todos los campos declarados (así no se rompe la
        # plantilla HTML), pero solo los configurados pueden ser obligatorios.
        for nombre_campo, campo in self.fields.items():
            if nombre_campo == 'plantilla':
                continue
            campo.required = False

        for clave in self.campos_requeridos:
            if clave in CAMPOS_SOLO_LECTURA:
                continue
            info = CATALOGO_CAMPOS.get(clave) or {}
            form_field = info.get('form_field', clave)
            if form_field in self.fields:
                self.fields[form_field].required = True
                if form_field == 'maestro_titular':
                    self.fields[form_field].error_messages['required'] = (
                        'El maestro titular es obligatorio.')
                elif form_field == 'maestro_interino':
                    self.fields[form_field].error_messages['required'] = (
                        'El maestro interino es obligatorio.')
                elif info.get('label'):
                    self.fields[form_field].error_messages['required'] = (
                        f"{info['label']} es obligatorio.")

        # Campos personalizados de esta plantilla (texto, fecha, número, lista).
        self.campos_personalizados = []
        if self.plantilla_seleccionada:
            for definicion in self.configuracion_plantilla.get('campos_personalizados') or []:
                variable = (definicion.get('variable') or '').strip()
                nombre_campo = nombre_campo_personalizado(self.plantilla_seleccionada.id, variable)
                if not nombre_campo:
                    continue
                campo = self._construir_campo_personalizado(definicion)
                self.fields[nombre_campo] = campo
                self.campos_personalizados.append({
                    'name': nombre_campo,
                    'label': campo.label,
                    'variable': variable,
                    'tipo': definicion.get('tipo') or 'texto',
                    'ayuda': definicion.get('ayuda') or '',
                    'requerido': bool(definicion.get('requerido')),
                    'bound': self[nombre_campo],
                })

    @staticmethod
    def _normalizar_pk(valor):
        if valor is None or valor == '':
            return None
        if hasattr(valor, 'pk'):
            return valor.pk
        try:
            return int(valor)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _construir_campo_personalizado(definicion):
        from django import forms as django_forms
        etiqueta = definicion.get('etiqueta') or definicion.get('variable') or 'Dato adicional'
        requerido = bool(definicion.get('requerido'))
        tipo = definicion.get('tipo') or 'texto'
        attrs = {'class': 'form-control'}
        if tipo == 'fecha':
            campo = django_forms.DateField(
                label=etiqueta, required=requerido,
                widget=django_forms.DateInput(
                    attrs={**attrs, 'type': 'date'}, format='%Y-%m-%d'),
            )
        elif tipo == 'numero':
            campo = django_forms.DecimalField(
                label=etiqueta, required=requerido,
                widget=django_forms.NumberInput(attrs={**attrs, 'step': 'any'}),
            )
        elif tipo == 'opciones':
            opciones = [
                (str(opcion), str(opcion))
                for opcion in (definicion.get('opciones') or [])
                if str(opcion).strip()
            ]
            campo = django_forms.ChoiceField(
                label=etiqueta, required=requerido,
                choices=[('', '--- Seleccione ---')] + opciones,
                widget=django_forms.Select(attrs=attrs),
            )
        elif tipo == 'texto_largo':
            campo = django_forms.CharField(
                label=etiqueta, required=requerido,
                widget=django_forms.Textarea(
                    attrs={**attrs, 'rows': 3, 'style': 'text-transform: uppercase;'}),
            )
        else:
            campo = django_forms.CharField(
                label=etiqueta, required=requerido,
                widget=django_forms.TextInput(
                    attrs={**attrs, 'style': 'text-transform: uppercase;'}),
            )
        campo.help_text = definicion.get('ayuda') or ''
        return campo

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
        required=False,
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

    # --- Campos para JUSTIFICACION DE RETROACTIVIDAD ---
    RAZON_RETRO_CHOICES = [
        ('', '--- Seleccione una opción ---'),
        ('firmas', 'Los tiempos que implicó la recabación de las firmas correspondientes'),
        ('presentacion', 'Que el maestro se presentó en esta fecha con su asignación'),
        ('usicamm', 'USICAMM asignó el (fecha) con lo cual apenas se presentó la asignación por parte del implicado en el oficio'),
        ('otro', 'Otro (especificar)'),
    ]
    opcionjustificacion = forms.ChoiceField(
        choices=RAZON_RETRO_CHOICES,
        label="Opción de Justificación",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_opcionjustificacion'})
    )
    razon_retroactividad = forms.ChoiceField(
        choices=RAZON_RETRO_CHOICES,
        label="Opción de Justificación",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_razon_retroactividad'})
    )
    fecha_usicamm = forms.DateField(
        label="Fecha de asignación USICAMM",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d')
    )
    texto_razon_otro = forms.CharField(
        label="Especifique la razón",
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control',
                                     'placeholder': 'Escriba aquí la razón de la justificación...'})
    )

    def clean(self):
        cleaned_data = super().clean()
        f1 = cleaned_data.get('fecha_efecto1')
        f2 = cleaned_data.get('fecha_efecto2')
        f3 = cleaned_data.get('fecha_efecto3')
        f4 = cleaned_data.get('fecha_efecto4')
        # La fecha inicial no puede ser mayor a la final; final vacía = sin fin.
        if f1 and f2 and f1 > f2:
            self.add_error(
                'fecha_efecto2',
                'La fecha inicial del titular no puede ser mayor a la fecha final. '
                'Deje la fecha final vacía si no tiene fin.'
            )
        if f3 and f4 and f3 > f4:
            self.add_error(
                'fecha_efecto4',
                'La fecha inicial del interino no puede ser mayor a la fecha final. '
                'Deje la fecha final vacía si no tiene fin.'
            )
        # El motivo debe pertenecer a la lista de la plantilla; las plantillas
        # sin motivo (lista vacía) no aceptan ninguno.
        plantilla = cleaned_data.get('plantilla')
        motivo = cleaned_data.get('motivo_tramite')
        plantilla_nombre = plantilla.nombre.upper().strip() if plantilla else ''

        if plantilla is not None and motivo:
            from gestion_escolar.motivos_plantilla import ids_permitidos
            permitidos = ids_permitidos(plantilla.nombre)
            if permitidos is not None and motivo.id not in permitidos:
                if not permitidos:
                    self.add_error(
                        'motivo_tramite',
                        f"La plantilla '{plantilla.nombre}' no lleva motivo de movimiento."
                    )
                else:
                    self.add_error(
                        'motivo_tramite',
                        f"El motivo '{motivo.motivo_tramite}' no corresponde a la plantilla '{plantilla.nombre}'."
                    )

        # Validación según la plantilla
        if plantilla_nombre == 'JUSTIFICACION DE RETROACTIVIDAD':
            opcion = (cleaned_data.get('opcionjustificacion') or cleaned_data.get('razon_retroactividad') or '').lower()
            if opcion == 'usicamm' and not cleaned_data.get('fecha_usicamm'):
                self.add_error('fecha_usicamm', 'Debe indicar la fecha de asignación USICAMM.')
            elif opcion == 'otro' and not (cleaned_data.get('texto_razon_otro') or '').strip():
                self.add_error('texto_razon_otro', 'Debe especificar la razón de la justificación.')
        # Los campos obligatorios se validan con la configuración de la
        # plantilla (campo.required), no con una regla fija en el código.

        return cleaned_data

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
        elegidos = set(self.cleaned_data['permissions'].values_list('pk', flat=True))
        # No quitar en silencio lo que la matriz no administra: conservar los
        # permisos actuales que no aparecen en ella (otras apps, permisos
        # residuales, etc.). Solo se agregan/quitan los visibles.
        from gestion_escolar.views.roles import get_permissions_matrix
        en_matriz = set()
        for seccion in get_permissions_matrix():
            for item in seccion['items']:
                if item['type'] == 'custom':
                    if item.get('permission'):
                        en_matriz.add(item['permission'].id)
                else:
                    for clave in ('view', 'add', 'change', 'delete'):
                        if item.get(clave):
                            en_matriz.add(item[clave].id)
        actuales = set(group.permissions.values_list('pk', flat=True))
        conservar = actuales - en_matriz
        group.permissions.set(list(elegidos | conservar))
        return group

class TemaForm(UppercaseFormMixin, forms.ModelForm):
    class Meta:
        model = Tema
        # 'usar_filtro_oscuro' ya no se expone: el velo se controla con
        # color_velo / opacidad_velo y la legibilidad la resuelven la sombra
        # en capas del texto y el chip translucido del menu.
        fields = ['nombre', 'activo', 'fecha_inicio', 'fecha_fin', 'color_principal', 'color_secundario', 'color_texto', 'color_dropdown', 'color_boton', 'imagen_fondo', 'color_velo', 'opacidad_velo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'imagen_fondo': forms.FileInput(attrs={'class': 'form-control'}),
            'opacidad_velo': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.05', 'min': '0', 'max': '1'}),
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