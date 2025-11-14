from django.contrib import admin
from .models import (
    Tema, Zona, Escuela, Categoria, Maestro, Director, MotivoTramite, 
    PlantillaTramite, Prelacion, TipoApreciacion, LoteReporteVacancia, 
    Vacancia, Historial, DocumentoExpediente, Correspondencia, 
    RegistroCorrespondencia, Notificacion, Pendiente, KardexMovimiento
)

@admin.register(Tema)
class TemaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'fecha_inicio', 'fecha_fin')
    list_filter = ('activo',)
    search_fields = ('nombre',)
    ordering = ('-activo', 'fecha_inicio',)
    fieldsets = (
        (None, {'fields': ('nombre', 'activo')}),
        ('Rango de Fechas', {'fields': ('fecha_inicio', 'fecha_fin')}),
        ('Apariencia', {'fields': ('color_principal', 'color_secundario', 'color_texto', 'imagen_fondo')}),
    )

@admin.register(Zona)
class ZonaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'supervisor')
    search_fields = ('numero',)

@admin.register(Escuela)
class EscuelaAdmin(admin.ModelAdmin):
    list_display = ('nombre_ct', 'zona_esc', 'turno', 'sostenimiento')
    search_fields = ('nombre_ct', 'id_escuela')

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id_categoria', 'descripcion')
    search_fields = ('id_categoria', 'descripcion')

@admin.register(Maestro)
class MaestroAdmin(admin.ModelAdmin):
    list_display = ('a_paterno', 'a_materno', 'nombres', 'rfc', 'curp')
    search_fields = ('a_paterno', 'a_materno', 'nombres', 'rfc', 'curp')

@admin.register(Director)
class DirectorAdmin(admin.ModelAdmin):
    list_display = ('maestro', 'escuela', 'fecha_inicio', 'fecha_fin')
    search_fields = ('maestro__nombres', 'escuela__nombre_ct')

@admin.register(MotivoTramite)
class MotivoTramiteAdmin(admin.ModelAdmin):
    list_display = ('motivo_tramite',)
    search_fields = ('motivo_tramite',)

@admin.register(PlantillaTramite)
class PlantillaTramiteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_documento')
    search_fields = ('nombre',)

@admin.register(Prelacion)
class PrelacionAdmin(admin.ModelAdmin):
    list_display = ('folio', 'nombre', 'curp', 'tipo_val')
    search_fields = ('folio', 'nombre', 'curp')

@admin.register(TipoApreciacion)
class TipoApreciacionAdmin(admin.ModelAdmin):
    list_display = ('descripcion',)
    search_fields = ('descripcion',)

@admin.register(LoteReporteVacancia)
class LoteReporteVacanciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario_generador', 'fecha_creacion', 'estado')
    search_fields = ('id',)

@admin.register(Vacancia)
class VacanciaAdmin(admin.ModelAdmin):
    list_display = ('maestro_titular', 'maestro_interino', 'tipo_vacante', 'fecha_inicio', 'fecha_final')
    search_fields = ('maestro_titular__nombres', 'maestro_interino__nombres')

@admin.register(Historial)
class HistorialAdmin(admin.ModelAdmin):
    list_display = ('tipo_documento', 'maestro', 'fecha_creacion')
    search_fields = ('tipo_documento', 'maestro__nombres')

@admin.register(DocumentoExpediente)
class DocumentoExpedienteAdmin(admin.ModelAdmin):
    list_display = ('maestro', 'tipo_documento', 'fecha_subida')
    search_fields = ('maestro__nombres', 'tipo_documento')

@admin.register(Correspondencia)
class CorrespondenciaAdmin(admin.ModelAdmin):
    list_display = ('asunto', 'remitente', 'destinatario', 'fecha_creacion', 'leido')
    search_fields = ('asunto', 'remitente__username', 'destinatario__username')

@admin.register(RegistroCorrespondencia)
class RegistroCorrespondenciaAdmin(admin.ModelAdmin):
    list_display = ('folio_documento', 'remitente', 'fecha_recibido', 'tipo_documento')
    search_fields = ('folio_documento', 'remitente')

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'mensaje', 'leida', 'fecha_creacion')
    search_fields = ('usuario__username', 'mensaje')

@admin.register(Pendiente)
class PendienteAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'usuario', 'fecha_programada', 'completado')
    search_fields = ('titulo', 'usuario__username')

@admin.register(KardexMovimiento)
class KardexMovimientoAdmin(admin.ModelAdmin):
    list_display = ('maestro', 'fecha', 'descripcion')
    search_fields = ('maestro__nombres',)