from django.contrib import admin
from .models import Tema

@admin.register(Tema)
class TemaAdmin(admin.ModelAdmin):
    """
    Configuración personalizada para el modelo Tema en el panel de administración.
    """
    list_display = (
        'nombre', 
        'activo', 
        'fecha_inicio', 
        'fecha_fin',
    )
    list_filter = ('activo',)
    search_fields = ('nombre',)
    ordering = ('-activo', 'fecha_inicio',)
    fieldsets = (
        (None, {'fields': ('nombre', 'activo')}),
        ('Rango de Fechas', {'fields': ('fecha_inicio', 'fecha_fin')}),
        ('Apariencia', {'fields': ('color_principal', 'color_secundario', 'color_texto', 'imagen_fondo')}),
    )