from django.contrib import admin
from .models import ConfiguracionGlobal, Marca, TipoEquipo, Equipo, HistorialDisponibilidad, Sistema, Servidor

@admin.register(Sistema)
class SistemaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'marca', 'created_at']
    search_fields = ['nombre']

@admin.register(Servidor)
class ServidorAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ip_address', 'tipo', 'sistema', 'estado', 'last_seen']
    list_filter = ['tipo', 'sistema', 'estado']
    search_fields = ['nombre', 'ip_address']

@admin.register(ConfiguracionGlobal)
class ConfiguracionGlobalAdmin(admin.ModelAdmin):
    list_display = ['tiempo_interrogacion', 'reintentos', 'umbral_falla_fibra', 'umbral_falla_celular']

@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ['nombre']

@admin.register(TipoEquipo)
class TipoEquipoAdmin(admin.ModelAdmin):
    list_display = ['nombre']

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ['id_equipo', 'ip', 'marca', 'tipo', 'estado', 'is_online', 'last_seen']
    list_filter = ['estado', 'marca', 'tipo', 'is_online', 'en_mantenimiento']
    search_fields = ['id_equipo', 'ip']

@admin.register(HistorialDisponibilidad)
class HistorialDisponibilidadAdmin(admin.ModelAdmin):
    list_display = ['equipo', 'timestamp', 'estado', 'latencia_ms']
    list_filter = ['estado', 'timestamp']
    search_fields = ['equipo__id_equipo']
