from django.urls import path
from . import views, views_export
from .views.health import health_check, readiness_check, liveness_check

urlpatterns = [
    # Health checks (for monitoring and load balancers)
    path('health/', health_check, name='health_check'),
    path('health/ready/', readiness_check, name='readiness_check'),
    path('health/live/', liveness_check, name='liveness_check'),
    
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('equipos/', views.EquipoListView.as_view(), name='equipo_list'),
    path('equipos/nuevo/', views.EquipoCreateView.as_view(), name='equipo_create'),
    path('equipos/<int:pk>/', views.EquipoDetailView.as_view(), name='equipo_detail'),
    path('equipos/<int:pk>/editar/', views.EquipoUpdateView.as_view(), name='equipo_update'),
    path('equipos/<int:pk>/eliminar/', views.EquipoDeleteView.as_view(), name='equipo_delete'),
    path('equipos/import/', views.ImportEquiposView.as_view(), name='import_equipos'),
    path('equipos/import/template/', views.DownloadImportTemplateView.as_view(), name='download_import_template'),
    path('reportes/', views.ReporteView.as_view(), name='reportes'),
    path('reportes/exportar/', views_export.ExportReportView.as_view(), name='export_report'),
    path('reportes/facturacion/', views.ReporteFacturacionView.as_view(), name='reporte_facturacion'),
    path('reportes/individual/', views.ReporteIndividualView.as_view(), name='reporte_individual'),
    path('reportes/individual/exportar/', views_export.ExportIndividualReportView.as_view(), name='export_individual_report'),
    path('equipos/<int:pk>/ping/', views.PingDeviceView.as_view(), name='ping_device'),
    path('equipos/<int:pk>/ping-modal/', views.PingModalView.as_view(), name='ping_modal'),
    path('equipos/<int:pk>/ping-tool/', views.PingToolView.as_view(), name='ping_tool'),
    path('search/', views.GlobalSearchView.as_view(), name='global_search'),
    path('mapa/', views.MapaView.as_view(), name='mapa'),
    
    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('cambiar-password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('mi-perfil/', views.MyProfileView.as_view(), name='my_profile'),
    
    # User management
    path('usuarios/', views.UsuarioListView.as_view(), name='usuario_list'),
    path('usuarios/<int:pk>/', views.UsuarioDetailView.as_view(), name='usuario_detail'),
    path('usuarios/nuevo/', views.UsuarioCreateView.as_view(), name='usuario_create'),
    path('usuarios/<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_update'),
    
    # Configuration
    path('configuracion/', views.ConfiguracionView.as_view(), name='configuracion'),
    path('configuracion/licencia/', views.LicenseSettingsView.as_view(), name='configuracion_licencia'),
    
    # Marcas CRUD
    path('marcas/', views.MarcaListView.as_view(), name='marca_list'),
    path('marcas/nueva/', views.MarcaCreateView.as_view(), name='marca_create'),
    path('marcas/<int:pk>/editar/', views.MarcaUpdateView.as_view(), name='marca_update'),
    path('marcas/<int:pk>/eliminar/', views.MarcaDeleteView.as_view(), name='marca_delete'),
    
    # TipoEquipo CRUD
    path('tipos/', views.TipoEquipoListView.as_view(), name='tipo_list'),
    path('tipos/nuevo/', views.TipoEquipoCreateView.as_view(), name='tipo_create'),
    path('tipos/<int:pk>/editar/', views.TipoEquipoUpdateView.as_view(), name='tipo_update'),
    path('tipos/<int:pk>/eliminar/', views.TipoEquipoDeleteView.as_view(), name='tipo_delete'),
    
    # Billing Calendar
    path('calendario/', views.CalendarioView.as_view(), name='calendario'),
    path('calendario/<int:anio>/<int:mes>/', views.CalendarioView.as_view(), name='calendario_mes'),
    path('eventos/', views.EventoListView.as_view(), name='evento_list'),
    path('eventos/nuevo/', views.EventoCreateView.as_view(), name='evento_create'),
    path('eventos/<int:pk>/editar/', views.EventoUpdateView.as_view(), name='evento_update'),
    path('eventos/<int:pk>/eliminar/', views.EventoDeleteView.as_view(), name='evento_delete'),
    
    # Portions
    path('porciones/', views.PorcionListView.as_view(), name='porcion_list'),
    path('porciones/nueva/', views.PorcionCreateView.as_view(), name='porcion_create'),
    path('porciones/<int:pk>/editar/', views.PorcionUpdateView.as_view(), name='porcion_update'),
    path('porciones/<int:pk>/eliminar/', views.PorcionDeleteView.as_view(), name='porcion_delete'),
    
    # Medidores
    path('medidores/', views.MedidorListView.as_view(), name='medidor_list'),
    path('medidores/exportar/', views.ExportMedidoresView.as_view(), name='export_medidores'),
    path('medidores/importar/', views.ImportMedidoresView.as_view(), name='import_medidores'),
    path('medidores/importar-colectores/', views.ImportColectoresView.as_view(), name='import_colectores'),
]
