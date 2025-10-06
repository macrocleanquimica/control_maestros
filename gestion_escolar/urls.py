from django.urls import path
from . import views

from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='index'),
    
    # URLs para Zonas
    path('zonas/', views.lista_zonas, name='lista_zonas'),
    path('zonas/agregar/', views.agregar_zona, name='agregar_zona'),
    path('zonas/editar/<int:pk>/', views.editar_zona, name='editar_zona'),
    path('zonas/detalle/<int:pk>/', views.detalle_zona, name='detalle_zona'),
    path('zonas/eliminar/<int:pk>/', views.eliminar_zona, name='eliminar_zona'),
    
    # URLs para Escuelas
    path('escuelas/', views.lista_escuelas, name='lista_escuelas'),
    path('escuelas/agregar/', views.agregar_escuela, name='agregar_escuela'),
    path('escuelas/editar/<int:pk>/', views.editar_escuela, name='editar_escuela'),
    path('escuelas/eliminar/<int:pk>/', views.eliminar_escuela, name='eliminar_escuela'),
    path('escuelas/detalle/<int:pk>/', views.detalle_escuela, name='detalle_escuela'),

    # URLs para Categorias
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/editar/<str:pk>/', views.editar_categoria, name='editar_categoria'),
    path('categorias/eliminar/<str:pk>/', views.eliminar_categoria, name='eliminar_categoria'),
    
    # URLs para Maestros - CAMBIO IMPORTANTE: usar <str:pk> en lugar de <int:pk>
    path('maestros/', views.lista_maestros, name='lista_maestros'),
    path('maestros/agregar/', views.agregar_maestro, name='agregar_maestro'),
    path('maestros/editar/<str:pk>/', views.editar_maestro, name='editar_maestro'),  # Cambiado a str
    path('maestros/eliminar/<str:pk>/', views.eliminar_maestro, name='eliminar_maestro'),  # Cambiado a str
    path('maestros/detalle/<str:pk>/', views.detalle_maestro, name='detalle_maestro'),
    path('maestros/detalle/<str:pk>/export/csv/', views.export_maestro_csv, name='export_maestro_csv'),
    path('maestros/eliminar_documento/<int:doc_pk>/', views.eliminar_documento_expediente, name='eliminar_documento_expediente'),
    
    # URLs para funciones específicas
    path('directores/', views.lista_directores, name='lista_directores'),
    path('supervisores-maestros/', views.lista_supervisores_maestros, name='lista_supervisores_maestros'),
    path('maestros-grupo/', views.lista_maestros_grupo, name='lista_maestros_grupo'),
    path('psicologos/', views.lista_psicologos, name='lista_psicologos'),
    path('trabajadores-sociales/', views.lista_trabajadores_sociales, name='lista_trabajadores_sociales'),
    path('docentes-apoyo/', views.lista_docentes_apoyo, name='lista_docentes_apoyo'),
    
    # URL genérica para cualquier función
    path('funcion/<str:funcion>/', views.lista_por_funcion, name='lista_por_funcion'),

    # URLs para Trámites
    path('tramites/generar/', views.generar_tramites_generales, name='generar_tramites_generales'),
    path('oficios/generar/', views.generar_oficios, name='generar_oficios'),
    path('tramites/get_motivos_tramite/', views.get_motivos_tramite_ajax, name='get_motivos_tramite_ajax'),
    path('tramites/get_maestro_data/', views.get_maestro_data_ajax, name='get_maestro_data'),
    path('buscar_maestros/', views.buscar_maestros_ajax, name='buscar_maestros_ajax'),

    # URLs para Reporte de Vacancia
    path('vacancias/gestionar/', views.gestionar_lote_vacancia, name='gestionar_lote_vacancia'),
    path('vacancias/exportar/<int:lote_id>/', views.exportar_lote_vacancia, name='exportar_lote_vacancia'),
    path('vacancias/get_maestro_data_ajax/', views.get_maestro_data_for_vacancia, name='get_maestro_data_for_vacancia'),
    path('vacancias/get_interino_data_ajax/', views.get_maestro_data_for_vacancia, name='get_interino_data_for_vacancia'),
    path('vacancias/get_interino_and_prelacion_data_ajax/', views.get_interino_and_prelacion_data_ajax, name='get_interino_and_prelacion_data_ajax'),
    path('vacancias/eliminar/<int:pk>/', views.eliminar_vacancia_lote, name='eliminar_vacancia_lote'),
    
    # NUEVA URL: Para obtener datos de prelación automáticamente
    path('tramites/get_prelacion_data/', views.get_prelacion_data_ajax, name='get_prelacion_data_ajax'),

    # URLs para Historial
    path('historial/', views.historial, name='historial'),
    path('historial/descargar/<int:item_id>/', views.descargar_archivo_historial, name='descargar_archivo_historial'),
    path('historial/eliminar/<int:item_id>/', views.eliminar_historial_item, name='eliminar_historial_item'),
    path('historial/guardar_observacion/<int:item_id>/', views.guardar_observacion_historial, name='guardar_observacion_historial'),
    path('historial/detalle_lote/<int:historial_id>/', views.historial_detalle_lote, name='historial_detalle_lote'),
    path('historial/detalle_tramite/<int:historial_id>/', views.historial_detalle_tramite, name='historial_detalle_tramite'),

    # URLs para Pendientes y Correspondencia
    path('pendientes/', views.PendienteActiveListView.as_view(), name='pendientes_activos'),
    path('pendientes/todos/', views.PendienteAllListView.as_view(), name='pendientes_todos'),
    path('pendientes/crear/', views.PendienteCreateView.as_view(), name='pendientes_crear'),
    path('pendientes/<int:pk>/completar/', views.pendiente_marcar_completado, name='pendiente_marcar_completado'),
    path('correspondencia/', views.CorrespondenciaInboxView.as_view(), name='correspondencia_inbox'),
    path('correspondencia/crear/', views.CorrespondenciaCreateView.as_view(), name='correspondencia_crear'),
    path('correspondencia/<int:pk>/', views.CorrespondenciaDetailView.as_view(), name='correspondencia_detail'),
    path('correspondencia/<int:pk>/eliminar/', views.correspondencia_eliminar, name='correspondencia_eliminar'),

    # URLs para Ajustes
    path('ajustes/', views.ajustes_view, name='ajustes'),
    path('ajustes/cambiar-password/', views.cambiar_password, name='cambiar_password'),
    path('ajustes/editar-perfil/', views.editar_perfil, name='editar_perfil'),
    path('ajustes/asignar-director/', views.asignar_director, name='asignar_director'),

    # URLs para Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),

    # URLs para Restablecimiento de Contraseña
    path('reset_password/', auth_views.PasswordResetView.as_view(template_name="gestion_escolar/password_reset/password_reset_form.html"), name="reset_password"),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(template_name="gestion_escolar/password_reset/password_reset_done.html"), name="password_reset_done"),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="gestion_escolar/password_reset/password_reset_confirm.html"), name="password_reset_confirm"),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name="gestion_escolar/password_reset/password_reset_complete.html"), name="password_reset_complete"),
]