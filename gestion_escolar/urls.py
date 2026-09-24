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
    
    # URLs para Mapa de Zonas
    path('mapa-zonas/', views.mapa_zonas, name='mapa_zonas'),
    path('mapa-zonas/pdf/', views.mapa_zonas_pdf, name='mapa_zonas_pdf'),

    # URLs para Escuelas
    path('escuelas/', views.lista_escuelas, name='lista_escuelas'),
    path('escuelas/agregar/', views.agregar_escuela, name='agregar_escuela'),
    path('escuelas/editar/<int:pk>/', views.editar_escuela, name='editar_escuela'),
    path('escuelas/eliminar/<int:pk>/', views.eliminar_escuela, name='eliminar_escuela'),
    path('escuelas/detalle/<int:pk>/', views.detalle_escuela, name='detalle_escuela'),
    path('escuelas/exportar/excel/', views.exportar_escuelas_excel, name='exportar_escuelas_excel'),

    # URLs para Categorias
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/editar/<str:pk>/', views.editar_categoria, name='editar_categoria'),
    path('categorias/eliminar/<str:pk>/', views.eliminar_categoria, name='eliminar_categoria'),
    
    # URLs para Maestros - CAMBIO IMPORTANTE: usar <str:pk> en lugar de <int:pk>
    path('maestros/', views.lista_maestros, name='lista_maestros'),
    path('maestros/ajax/', views.lista_maestros_ajax, name='lista_maestros_ajax'),
    path('maestros/agregar/', views.agregar_maestro, name='agregar_maestro'),
    path('maestros/editar/<str:pk>/', views.editar_maestro, name='editar_maestro'),
    path('maestros/eliminar/<str:pk>/', views.eliminar_maestro, name='eliminar_maestro'),
    path('maestros/detalle/<str:pk>/', views.detalle_maestro, name='detalle_maestro'),
    path('maestros/agregar-plaza/<str:pk>/', views.agregar_otra_plaza, name='agregar_otra_plaza'),
    path('maestros/detalle/<str:pk>/export/excel/', views.export_maestro_excel, name='export_maestro_excel'),
    path('maestros/exportar/excel/', views.exportar_maestros_excel, name='exportar_maestros_excel'),
    path('maestros/eliminar_documento/<int:doc_pk>/', views.eliminar_documento_expediente, name='eliminar_documento_expediente'),
    
    # URLs para funciones específicas
    path('directores/', views.lista_directores, name='lista_directores'),
    path('supervisores-maestros/', views.lista_supervisores_maestros, name='lista_supervisores_maestros'),
    path('maestros-grupo/', views.lista_maestros_grupo, name='lista_maestros_grupo'),
    path('psicologos/', views.lista_psicologos, name='lista_psicologos'),
    path('trabajadores-sociales/', views.lista_trabajadores_sociales, name='lista_trabajadores_sociales'),
    path('docentes-apoyo/', views.lista_docentes_apoyo, name='lista_docentes_apoyo'),
    path('reportes/personas-vs-plazas/', views.reporte_personas_vs_plazas, name='reporte_personas_vs_plazas'),
    
    # URL genérica para cualquier función
    path('funcion/<str:funcion>/', views.lista_por_funcion, name='lista_por_funcion'),

    # URLs para Trámites
    path('tramites/generar/', views.generar_tramites_generales, name='generar_tramites_generales'),
    path('oficios/generar/', views.generar_oficios, name='generar_oficios'),
    path('tramites/get_motivos_tramite/', views.get_motivos_tramite_ajax, name='get_motivos_tramite_ajax'),
    path('tramites/get_maestro_data/', views.get_maestro_data_ajax, name='get_maestro_data'),
    path('buscar_maestros/', views.buscar_maestros_ajax, name='buscar_maestros_ajax'),
    path('buscar_escuelas/', views.buscar_escuelas_ajax, name='buscar_escuelas_ajax'),

    # URLs para Reporte de Vacancia
    path('vacancias/gestionar/', views.gestionar_lote_vacancia, name='gestionar_lote_vacancia'),
    path('vacancias/gestionar/<int:lote_id>/', views.gestionar_lote_vacancia, name='gestionar_lote_vacancia_con_id'),
    path('vacancias/exportar/paso_word/<int:lote_id>/', views.exportar_paso_word, name='exportar_paso_word'),
    path('vacancias/exportar/paso_gsheets/<int:lote_id>/', views.exportar_paso_gsheets, name='exportar_paso_gsheets'),
    path('vacancias/exportar/paso_excel/<int:lote_id>/', views.exportar_paso_excel, name='exportar_paso_excel'),
    path('vacancias/exportar/paso_excel_eo/<int:lote_id>/', views.exportar_paso_excel_eo, name='exportar_paso_excel_eo'),
    path('vacancias/get_maestro_data_ajax/', views.get_maestro_data_for_vacancia, name='get_maestro_data_for_vacancia'),
    path('vacancias/get_interino_data_ajax/', views.get_maestro_data_for_vacancia, name='get_interino_data_for_vacancia'),
    path('vacancias/get_interino_and_prelacion_data_ajax/', views.get_interino_and_prelacion_data_ajax, name='get_interino_and_prelacion_data_ajax'),
    path('vacancias/eliminar/<int:pk>/', views.eliminar_vacancia_lote, name='eliminar_vacancia_lote'),
    path('vacancias/lotes/', views.lista_lotes_vacancia, name='lista_lotes_vacancia'),
    path('vacancias/lotes/<int:lote_id>/cancelar/', views.cancelar_lote_vacancia, name='cancelar_lote_vacancia'),
    path('reportes/vacancias/', views.reporte_vacancias_fecha, name='reporte_vacancias_fecha'),
    path('reportes/vacancias/exportar/', views.exportar_reporte_vacancias_excel, name='exportar_reporte_vacancias_excel'),
    path('tramites/get_prelacion_data/', views.get_prelacion_data_ajax, name='get_prelacion_data_ajax'),

    # URLs para Historial
    path('historial/', views.historial, name='historial'),
    path('historial/descargar/<int:item_id>/', views.descargar_archivo_historial, name='descargar_archivo_historial'),
    path('historial/eliminar/<int:item_id>/', views.eliminar_historial_item, name='eliminar_historial_item'),
    path('historial/guardar_observacion/<int:item_id>/', views.guardar_observacion_historial, name='guardar_observacion_historial'),
    path('historial/detalle_lote/<int:historial_id>/', views.historial_detalle_lote, name='historial_detalle_lote'),
    path('historial/detalle_tramite/<int:historial_id>/', views.historial_detalle_tramite, name='historial_detalle_tramite'),
    path('historial/corregir/<int:item_id>/', views.corregir_tramite, name='corregir_tramite'),

    # URLs para Reportes
    path('reportes/', views.reportes_dashboard, name='reportes_dashboard'),
    path('reportes/personal_fuera_adscripcion/', views.reporte_personal_fuera_adscripcion, name='reporte_personal_fuera_adscripcion'),
    path('reportes/distribucion_funcion/', views.reporte_distribucion_funcion, name='reporte_distribucion_funcion'),
    path('reportes/personal_fuera_adscripcion/export/excel/', views.export_personal_fuera_adscripcion_excel, name='export_personal_fuera_adscripcion_excel'),
    path('reportes/exportar/horizontal/', views.exportar_maestros_personalizado_excel, name='exportar_maestros_personalizado_excel'),
    path('reportes/reporteador/', views.reporteador_datos, name='reporteador_datos'),
    path('reportes/reporteador/exportar/', views.exportar_datos_dinamicos_excel, name='exportar_datos_dinamicos_excel'),
    path('reportes/centros_trabajo/pdf/', views.reporte_centros_trabajo_pdf, name='reporte_centros_trabajo_pdf'),

    # URLs para Pendientes y Correspondencia
    path('pendientes/', views.PendienteActiveListView.as_view(), name='pendientes_activos'),
    path('pendientes/todos/', views.PendienteAllListView.as_view(), name='pendientes_todos'),
    path('pendientes/crear/', views.PendienteCreateView.as_view(), name='pendientes_crear'),
    path('pendientes/<int:pk>/completar/', views.pendiente_marcar_completado, name='pendiente_marcar_completado'),
    path('correspondencia/', views.CorrespondenciaInboxView.as_view(), name='correspondencia_inbox'),
    path('correspondencia/crear/', views.CorrespondenciaCreateView.as_view(), name='correspondencia_crear'),
    path('correspondencia/<int:pk>/', views.CorrespondenciaDetailView.as_view(), name='correspondencia_detail'),
    path('correspondencia/<int:pk>/eliminar/', views.correspondencia_eliminar, name='correspondencia_eliminar'),

    # URLs para Registro de Correspondencia
    path('registros_correspondencia/', views.RegistroCorrespondenciaListView.as_view(), name='registrocorrespondencia_list'),
    path('registros_correspondencia/nuevo/', views.RegistroCorrespondenciaCreateView.as_view(), name='registrocorrespondencia_create'),
    path('registros_correspondencia/<int:pk>/', views.RegistroCorrespondenciaDetailView.as_view(), name='registrocorrespondencia_detail'),
    path('registros_correspondencia/<int:pk>/editar/', views.RegistroCorrespondenciaUpdateView.as_view(), name='registrocorrespondencia_update'),
    path('registros_correspondencia/<int:pk>/eliminar/', views.RegistroCorrespondenciaDeleteView.as_view(), name='registrocorrespondencia_delete'),

    # URLs para Ajustes
    path('ajustes/', views.ajustes_view, name='ajustes'),
    path('ajustes/cambiar-password/', views.cambiar_password, name='cambiar_password'),
    path('ajustes/editar-perfil/', views.editar_perfil, name='editar_perfil'),
    path('ajustes/asignar-director/', views.asignar_director, name='asignar_director'),

    # URLs para Roles y Permisos
    path('ajustes/roles/', views.RoleListView.as_view(), name='role_list'),
    path('ajustes/roles/nuevo/', views.RoleCreateView.as_view(), name='role_create'),
    path('ajustes/roles/<int:pk>/editar/', views.RoleUpdateView.as_view(), name='role_update'),
    path('ajustes/roles/<int:pk>/miembros/', views.manage_role_members, name='role_members'),
    path('ajustes/roles/<int:pk>/eliminar/', views.RoleDeleteView.as_view(), name='role_delete'),

    # URLs para Gestión de Usuarios (Admin)
    path('ajustes/usuarios/', views.UserListView.as_view(), name='user_list'),
    path('ajustes/usuarios/ajax/', views.user_datatable_ajax, name='user_datatable_ajax'),
    path('ajustes/usuarios/nuevo/', views.UserCreateView.as_view(), name='user_create'),
    path('ajustes/usuarios/<int:pk>/editar/', views.UserUpdateView.as_view(), name='user_update'),
    path('ajustes/usuarios/<int:pk>/password/', views.UserPasswordChangeView.as_view(), name='user_password_change'),
    path('ajustes/usuarios/<int:pk>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    path('ajustes/usuarios/<int:pk>/detalle/', views.UserDetailView.as_view(), name='user_detail'),

    # URLs para Gestión de Temas
    path('ajustes/temas/', views.ThemeListView.as_view(), name='tema_list'),
    path('ajustes/temas/nuevo/', views.ThemeCreateView.as_view(), name='tema_create'),
    path('ajustes/temas/<int:pk>/editar/', views.ThemeUpdateView.as_view(), name='tema_update'),
    path('ajustes/temas/<int:pk>/eliminar/', views.ThemeDeleteView.as_view(), name='tema_delete'),

    # URLs para Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),

    # URLs para Restablecimiento de Contraseña
    path('reset_password/', auth_views.PasswordResetView.as_view(template_name="gestion_escolar/password_reset/password_reset_form.html"), name="reset_password"),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(template_name="gestion_escolar/password_reset/password_reset_done.html"), name="password_reset_done"),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="gestion_escolar/password_reset/password_reset_confirm.html"), name="password_reset_confirm"),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name="gestion_escolar/password_reset/password_reset_complete.html"), name="password_reset_complete"),

    # URLs para FUP
    path('fup/', views.lista_fup, name='lista_fup'),
    path('fup/ajax/', views.fup_datatable_ajax, name='fup_datatable_ajax'),
    path('fup/exportar/excel/', views.exportar_fup_excel, name='exportar_fup_excel'),
    path('fup/reporte-zona/', views.reporte_fups_opciones, name='reporte_fups_opciones'),
    path('fup/reporte-zona/exportar/', views.exportar_fups_zona_excel, name='exportar_fups_zona_excel'),
    path('fup/crear/', views.crear_fup, name='crear_fup'),
    path('fup/editar/<int:pk>/', views.editar_fup, name='editar_fup'),
    path('fup/eliminar/<int:pk>/', views.eliminar_fup, name='eliminar_fup'),
    path('fup/detalle/<int:pk>/', views.detalle_fup, name='detalle_fup'),
    path('fup/get_maestro_data/', views.get_maestro_data_fup, name='get_maestro_data_fup'),
    path('fup/validar_folio/', views.validar_folio_fup, name='validar_folio_fup'),

    # URLs para Kardex
    path('kardex/ajax/', views.kardex_maestros_ajax, name='kardex_maestros_ajax'),
    path('kardex/', views.kardex_maestro_list, name='kardex_list'),
    path('kardex/maestro/<str:maestro_id>/', views.kardex_maestro_detail, name='kardex_maestro_detail'),

    # URLs para Prelación
    path('prelacion/', views.lista_prelacion, name='lista_prelacion'),
    path('prelacion/ajax/', views.lista_prelacion_ajax, name='lista_prelacion_ajax'),
    path('prelacion/importar/', views.importar_prelacion_excel, name='importar_prelacion_excel'),
    path('prelacion/descargar/', views.descargar_prelacion_excel, name='descargar_prelacion_excel'),
]
