from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from .models import Zona, Escuela, Maestro, Categoria, MotivoTramite, PlantillaTramite, Prelacion, Director, DocumentoExpediente
from .forms import DocumentoExpedienteForm

# Register your models here.






from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'groups')
    actions = ['activate_users']

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
    activate_users.short_description = "Activar usuarios seleccionados"

# Anular el registro del UserAdmin por defecto y registrar el personalizado
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

admin.site.register(Prelacion)
import re

# Función de validación del CCT
def validar_formato_cct(cct):
    """
    Validar formato del CCT: 2 dígitos + 3 letras + 4 dígitos + 1 letra
    Ejemplo: 10DML0013Q
    """
    if not cct or len(str(cct)) != 10:
        return False
    
    patron = r'^\d{2}[A-Za-z]{3}\d{4}[A-Za-z]$'
    return bool(re.match(patron, str(cct)))

# Resource para Escuela
class EscuelaResource(resources.ModelResource):
    # Mapeo de campos personalizados para coincidir con tu Excel
    id_escuelas = fields.Field(attribute='id_escuela', column_name='id_escuelas')
    Zona_Esc = fields.Field(
        attribute='zona_esc',
        column_name='Zona_Esc',
        widget=ForeignKeyWidget(Zona, 'numero')
    )
    Nombre_CT = fields.Field(attribute='nombre_ct', column_name='Nombre_CT')
    Turno = fields.Field(attribute='turno', column_name='Turno')
    Domicilio = fields.Field(attribute='domicilio', column_name='Domicilio')
    Tel_CT = fields.Field(attribute='telefono_ct', column_name='Tel_CT')
    Zona_Economica = fields.Field(attribute='zona_economica', column_name='Zona_Economica')
    Region = fields.Field(attribute='region', column_name='Region')
    U_D = fields.Field(attribute='u_d', column_name='U_D')
    Sostenimiento = fields.Field(attribute='sostenimiento', column_name='Sostenimiento')

    class Meta:
        model = Escuela
        import_id_fields = ['id_escuela']
        skip_unchanged = True
        report_skipped = True
        use_bulk = True
        batch_size = 1000
        fields = (
            'id_escuelas', 'Zona_Esc', 'Nombre_CT', 'Turno', 'Domicilio', 
            'Tel_CT', 'Zona_Economica', 'Region', 'U_D', 'Sostenimiento'
        )
        export_order = (
            'id_escuelas', 'Zona_Esc', 'Nombre_CT', 'Turno', 'Domicilio', 
            'Tel_CT', 'Zona_Economica', 'Region', 'U_D', 'Sostenimiento'
        )

    def before_import_row(self, row, **kwargs):
        """Validaciones previas a la importación"""
        # Validar CCT
        cct = row.get('id_escuelas')
        if cct and not validar_formato_cct(cct):
            raise ValueError(f"Formato de CCT inválido: {cct}. Debe ser: 2 dígitos + 3 letras + 4 dígitos + 1 letra")
        
        # Manejar la conversión de la zona
        zona_numero = row.get('Zona_Esc')
        if zona_numero:
            try:
                # Convertir a entero si es necesario
                if isinstance(zona_numero, str) and zona_numero.isdigit():
                    zona_numero = int(zona_numero)
                
                zona = Zona.objects.get(numero=zona_numero)
                row['Zona_Esc'] = zona.id
            except Zona.DoesNotExist:
                raise ValueError(f"La zona {zona_numero} no existe. Debe crearla primero.")
            except ValueError:
                raise ValueError(f"Valor inválido para zona: {zona_numero}")

    def get_instance(self, instance_loader, row):
        """Buscar instancia existente por id_escuela"""
        try:
            return Escuela.objects.get(id_escuela=row['id_escuelas'])
        except Escuela.DoesNotExist:
            return None

    def import_row(self, row, instance_loader, **kwargs):
        """Manejo personalizado de errores"""
        try:
            return super().import_row(row, instance_loader, **kwargs)
        except Exception as e:
            # Log del error
            print(f"Error importando fila: {row}. Error: {str(e)}")
            raise

# Admin para Zona
@admin.register(Zona)
class ZonaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'get_inferred_supervisor', 'observaciones')
    search_fields = ('numero',)
    list_filter = ('numero',)

    def get_inferred_supervisor(self, obj):
        # Lógica para inferir el supervisor desde Maestro -> Escuela -> Zona
        supervisor_values = ['SUPERVISOR', 'SUPERVISOR (A)', 'SUPERVISOR(A)']
        supervisor_maestro = Maestro.objects.filter(
            funcion__in=supervisor_values,
            id_escuela__zona_esc=obj
        ).first()
        if supervisor_maestro:
            return f"{supervisor_maestro.nombres} {supervisor_maestro.a_paterno} {supervisor_maestro.a_materno}"
        return "Sin supervisor asignado"
    
    get_inferred_supervisor.short_description = 'Supervisor'

# Admin para Escuela
@admin.register(Escuela)
class EscuelaAdmin(ImportExportModelAdmin):
    resource_class = EscuelaResource
    list_display = ('id_escuela', 'nombre_ct', 'zona_esc', 'turno', 'zona_economica', 'u_d', 'sostenimiento')
    search_fields = ('id_escuela', 'nombre_ct', 'zona_esc__numero')
    list_filter = ('zona_esc', 'turno', 'zona_economica', 'u_d', 'sostenimiento', 'region')
    readonly_fields = ('fecha_registro', 'fecha_actualizacion')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id_escuela', 'nombre_ct', 'zona_esc', 'turno')
        }),
        ('Ubicación', {
            'fields': ('domicilio', 'telefono_ct', 'region', 'zona_economica')
        }),
        ('Administrativo', {
            'fields': ('u_d', 'sostenimiento')
        }),
        ('Auditoría', {
            'fields': ('fecha_registro', 'fecha_actualizacion'),
            'classes': ('collapse',)
        })
    )
    
    # Mostrar ayuda para el formato del CCT en el listado
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['id_escuela'].help_text = "Formato: 10DML0013Q (2 dígitos + 3 letras + 4 dígitos + 1 letra)"
        return form

class DocumentoExpedienteInline(admin.TabularInline):
    model = DocumentoExpediente
    form = DocumentoExpedienteForm
    extra = 1  # Número de formularios extra para mostrar
    readonly_fields = ('fecha_subida', 'subido_por')
    fields = ('tipo_documento', 'archivo', 'fecha_subida', 'subido_por')

# Admin para Maestro
@admin.register(Maestro)
class MaestroAdmin(admin.ModelAdmin):
    inlines = [DocumentoExpedienteInline]
    list_display = ('id_maestro', 'a_paterno', 'a_materno', 'nombres', 'curp', 'id_escuela', 'status')
    search_fields = ('id_maestro', 'a_paterno', 'a_materno', 'nombres', 'curp')
    list_filter = ('sexo', 'est_civil', 'nivel_estudio', 'status', 'id_escuela')
    readonly_fields = ('fecha_ingreso',)
    menu_group = None  # Esto elimina el submenú "Todos los maestros"

# Admin para DocumentoExpediente (opcional, para gestión directa)
@admin.register(DocumentoExpediente)
class DocumentoExpedienteAdmin(admin.ModelAdmin):
    list_display = ('maestro', 'tipo_documento', 'get_file_name', 'fecha_subida', 'subido_por')
    list_filter = ('tipo_documento', 'fecha_subida', 'maestro')
    search_fields = ('maestro__nombres', 'maestro__a_paterno', 'archivo')
    readonly_fields = ('fecha_subida', 'subido_por')

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Si es un objeto nuevo
            obj.subido_por = request.user
        super().save_model(request, obj, form, change)


# Admin para Director
@admin.register(Director)
class DirectorAdmin(admin.ModelAdmin):
    list_display = ('maestro', 'escuela', 'fecha_inicio', 'fecha_fin')
    search_fields = ('maestro__a_paterno', 'maestro__a_materno', 'maestro__nombres', 'escuela__nombre_ct')
    list_filter = ('fecha_inicio', 'fecha_fin')



# Admin para Categoria
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id_categoria', 'descripcion')
    search_fields = ('id_categoria', 'descripcion')

class MotivoTramiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'motivo_tramite')
    search_fields = ('motivo_tramite',)

admin.site.register(MotivoTramite, MotivoTramiteAdmin)

class PlantillaTramiteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ruta_archivo')
    search_fields = ('nombre',)

admin.site.register(PlantillaTramite, PlantillaTramiteAdmin)

from .models import RegistroCorrespondencia

@admin.register(RegistroCorrespondencia)
class RegistroCorrespondenciaAdmin(admin.ModelAdmin):
    list_display = ('folio_documento', 'remitente', 'tipo_documento', 'fecha_recibido', 'maestro', 'archivo_adjunto')
    search_fields = ('folio_documento', 'remitente', 'contenido', 'maestro__nombres', 'maestro__a_paterno')
    list_filter = ('tipo_documento', 'area', 'fecha_recibido')
    date_hierarchy = 'fecha_recibido'
    readonly_fields = ('fecha_registro',)