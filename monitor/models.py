from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SingletonModel, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class ConfiguracionGlobal(SingletonModel):
    tiempo_interrogacion = models.IntegerField(default=60, help_text="Tiempo entre pings en segundos")
    reintentos = models.IntegerField(default=3, help_text="Número de reintentos antes de marcar offline")
    umbral_falla_fibra = models.IntegerField(default=60, help_text="Tiempo offline para alerta Fibra (segundos)")
    umbral_falla_celular = models.IntegerField(default=300, help_text="Tiempo offline para alerta Celular (segundos)")

    class Meta:
        verbose_name = "Configuración Global"
        verbose_name_plural = "Configuración Global"

    def __str__(self):
        return "Configuración del Sistema"

class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    color = models.CharField(
        max_length=7,
        default='#6B7280',
        help_text='Color hexadecimal para visualización (ej: #3B82F6)'
    )
    
    def __str__(self):
        return self.nombre

class TipoEquipo(models.Model):
    nombre = models.CharField(max_length=100, unique=True) # Router, Switch, Colector, etc.

    def __str__(self):
        return self.nombre

class Equipo(models.Model):
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
    ]
    MEDIO_CHOICES = [
        ('FIBRA', 'Fibra Óptica'),
        ('CELULAR', 'Celular (4G/5G)'),
    ]

    id_equipo = models.CharField(max_length=50, unique=True, verbose_name="ID Equipo")
    ip = models.GenericIPAddressField(unique=True)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True)
    tipo = models.ForeignKey(TipoEquipo, on_delete=models.SET_NULL, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ACTIVO')
    en_mantenimiento = models.BooleanField(default=False)
    medio_comunicacion = models.CharField(max_length=20, choices=MEDIO_CHOICES, default='FIBRA')
    
    # Ubicación
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    
    # Metadatos extra
    poste = models.CharField(max_length=50, blank=True, null=True)
    piloto = models.CharField(max_length=100, blank=True, null=True)
    canasta = models.BooleanField(default=False)
    permisos = models.BooleanField(default=False)

    last_seen = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id_equipo} ({self.ip})"

    def get_status(self):
        """
        Evalúa si el equipo está online basado en last_seen y el medio de comunicación.
        Retorna (bool_online, reason)
        """
        if not self.last_seen:
            return False, "Nunca visto"
        
        config = ConfiguracionGlobal.load()
        threshold = config.umbral_falla_fibra if self.medio_comunicacion == 'FIBRA' else config.umbral_falla_celular
        
        delta = (timezone.now() - self.last_seen).total_seconds()
        if delta > threshold:
            return False, f"Timeout ({int(delta)}s > {threshold}s)"
        return True, "Online"

class HistorialDisponibilidad(models.Model):
    ESTADO_CHOICES = [
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline'),
        ('TIMEOUT', 'Timeout'),
        ('MAINTENANCE', 'Mantenimiento'),
    ]

    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='historial')
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    latencia_ms = models.FloatField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    packet_loss = models.FloatField(default=0.0)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'equipo']),
        ]

    def __str__(self):
        return f"{self.equipo} - {self.timestamp}: {self.estado}"


class Porcion(models.Model):
    """Porción de clientes para facturación."""
    TIPO_CHOICES = [
        ('MASIVO', 'Masivo'),
        ('ESPECIAL', 'Especial'),
    ]
    
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Porción'
        verbose_name_plural = 'Porciones'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class CicloFacturacion(models.Model):
    """Ciclo de facturación mensual."""
    TIPO_CHOICES = [
        ('MASIVO', 'Masivo'),
        ('ESPECIAL', 'Especial'),
    ]
    
    mes = models.IntegerField(verbose_name='Mes', help_text='1-12')
    anio = models.IntegerField(verbose_name='Año')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Ciclo de Facturación'
        verbose_name_plural = 'Ciclos de Facturación'
        unique_together = [['mes', 'anio', 'tipo']]
        ordering = ['-anio', '-mes', 'tipo']
    
    def __str__(self):
        meses = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        return f"{meses.get(self.mes, self.mes)} {self.anio} - {self.get_tipo_display()}"


class EventoFacturacion(models.Model):
    """Evento de facturación (prefacturación o facturación) para una porción."""
    TIPO_EVENTO_CHOICES = [
        ('PREFACTURACION', 'Prefacturación'),
        ('FACTURACION', 'Facturación'),
    ]
    
    ciclo = models.ForeignKey(CicloFacturacion, on_delete=models.CASCADE, related_name='eventos', verbose_name='Ciclo')
    porcion = models.ForeignKey(Porcion, on_delete=models.CASCADE, related_name='eventos', verbose_name='Porción')
    tipo_evento = models.CharField(max_length=20, choices=TIPO_EVENTO_CHOICES, verbose_name='Tipo de Evento')
    fecha = models.DateField(verbose_name='Fecha')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Evento de Facturación'
        verbose_name_plural = 'Eventos de Facturación'
        ordering = ['fecha', 'tipo_evento']
    
    def __str__(self):
        return f"{self.get_tipo_evento_display()} {self.porcion.nombre} - {self.fecha}"
    
    def get_color(self):
        """Retorna el color del evento basado en el tipo de evento y tipo de porción."""
        if self.porcion.tipo == 'MASIVO':
            if self.tipo_evento == 'PREFACTURACION':
                return '#FFC0CB'  # Rosa (pink)
            else:  # FACTURACION
                return '#DC2626'  # Rojo (red)
        else:  # ESPECIAL
            if self.tipo_evento == 'PREFACTURACION':
                return '#87CEEB'  # Celeste (sky blue)
            else:  # FACTURACION
                return '#2563EB'  # Azul (blue)
    
    def get_display_name(self):
        """Retorna el nombre para mostrar en el calendario."""
        return f"{self.get_tipo_evento_display()} {self.porcion.nombre}"


class UserProfile(models.Model):
    """Extended user profile with role and avatar."""
    
    ROLE_CHOICES = [
        ('operator', 'Operador'),
        ('admin', 'Administrador'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='operator', verbose_name='Rol')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='Avatar')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    def get_full_name(self):
        """Return full name or username."""
        if self.user.first_name or self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}".strip()
        return self.user.username
