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
    
    # Configuración SNMP v3
    snmp_user = models.CharField(max_length=100, default='', blank=True, verbose_name="Usuario SNMP v3")
    
    AUTH_PROTOCOL_CHOICES = [
        ('MD5', 'MD5'),
        ('SHA', 'SHA'),
        ('NONE', 'None'),
    ]
    snmp_auth_protocol = models.CharField(max_length=10, choices=AUTH_PROTOCOL_CHOICES, default='SHA', verbose_name="Protocolo Autenticación")
    snmp_auth_key = models.CharField(max_length=100, default='', blank=True, verbose_name="Clave Autenticación")
    
    PRIV_PROTOCOL_CHOICES = [
        ('DES', 'DES'),
        ('AES', 'AES'),
        ('NONE', 'None'),
    ]
    snmp_priv_protocol = models.CharField(max_length=10, choices=PRIV_PROTOCOL_CHOICES, default='AES', verbose_name="Protocolo Privacidad")
    snmp_priv_key = models.CharField(max_length=100, default='', blank=True, verbose_name="Clave Privacidad")

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
        ('EN_MANTENIMIENTO', 'En Mantenimiento'),
    ]
    MEDIO_CHOICES = [
        ('FIBRA', 'Fibra Óptica'),
        ('CELULAR', 'Celular'),
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

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                # Load existing instance from DB to detect what changed
                old_instance = Equipo.objects.get(pk=self.pk)
                
                # Case 1: 'estado' changed (likely via Edit Form)
                if self.estado != old_instance.estado:
                    if self.estado == 'EN_MANTENIMIENTO':
                        self.en_mantenimiento = True
                    elif old_instance.estado == 'EN_MANTENIMIENTO':
                        self.en_mantenimiento = False
                
                # Case 2: 'en_mantenimiento' changed (likely via Toggle Button)
                # This only runs if 'estado' didn't change, or both were set manually
                elif self.en_mantenimiento != old_instance.en_mantenimiento:
                    if self.en_mantenimiento:
                        self.estado = 'EN_MANTENIMIENTO'
                    elif self.estado == 'EN_MANTENIMIENTO':
                        self.estado = 'ACTIVO'
            except Equipo.DoesNotExist:
                pass
        else:
            # New record logic
            if self.estado == 'EN_MANTENIMIENTO':
                self.en_mantenimiento = True
            elif self.en_mantenimiento:
                self.estado = 'EN_MANTENIMIENTO'

        super().save(*args, **kwargs)

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
            return '#EF5350'  # Rojo pálido para facturación masiva
        else:  # ESPECIAL
            return '#87CEEB'  # Celeste claro para facturación especial
    
    def get_display_name(self):
        """Retorna el nombre para mostrar en el calendario."""
        return f"{self.get_tipo_evento_display()} {self.porcion.nombre}"


from django.core.exceptions import ValidationError

def validate_avatar(image):
    """Validate avatar image file type and size."""
    # Validate file extension
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ext = image.name.lower().split('.')[-1]
    if f'.{ext}' not in valid_extensions:
        raise ValidationError(
            f'Tipo de archivo no permitido. Solo se aceptan: {", ".join(valid_extensions)}'
        )
    
    # Validate file size (max 2MB)
    max_size = 2 * 1024 * 1024  # 2MB
    if image.size > max_size:
        raise ValidationError(
            f'El archivo es muy grande ({image.size / (1024*1024):.2f}MB). Tamaño máximo: 2MB'
        )


class UserProfile(models.Model):
    """Extended user profile with role and avatar."""
    
    ROLE_CHOICES = [
        ('operator', 'Operador'),
        ('admin', 'Administrador'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='operator', verbose_name='Rol')
    avatar = models.ImageField(
        upload_to='avatars/', 
        null=True, 
        blank=True, 
        verbose_name='Avatar',
        validators=[validate_avatar],
        help_text='Formatos permitidos: JPG, PNG, GIF, WEBP. Tamaño máximo: 2MB'
    )
    
    # Notification preferences
    telegram_chat_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Chat ID de Telegram',
        help_text='ID del chat de Telegram para recibir notificaciones. Para obtenerlo, habla con @userinfobot'
    )
    email_notifications = models.BooleanField(
        default=True,
        verbose_name='Notificaciones por Email',
        help_text='Recibir alertas de equipos críticos por correo electrónico'
    )
    telegram_notifications = models.BooleanField(
        default=False,
        verbose_name='Notificaciones por Telegram',
        help_text='Recibir alertas de equipos críticos por Telegram'
    )
    
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


class Medidor(models.Model):
    """Medidor AMI (Advanced Metering Infrastructure)."""
    MARCA_CHOICES = [
        ('HONEYWELL', 'Honeywell'),
        ('TRILLIANT', 'Trilliant'),
        ('ITRON', 'Itron'),
        ('HEXING', 'Hexing'),
    ]
    
    numero = models.CharField(max_length=100, unique=True, verbose_name='Número de Medidor')
    marca = models.CharField(max_length=20, choices=MARCA_CHOICES, verbose_name='Marca')
    porcion = models.ForeignKey(Porcion, on_delete=models.CASCADE, related_name='medidores', verbose_name='Porción')
    colector = models.ForeignKey(
        'Equipo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medidores_asociados',
        verbose_name='Colector Asociado'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Medidor'
        verbose_name_plural = 'Medidores'
        ordering = ['numero']
    
    def __str__(self):
        return f"{self.numero} ({self.marca})"


class Sistema(models.Model):
    """Agrupación de servidores (HES, etc)."""
    nombre = models.CharField(max_length=100, unique=True)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Sistema'
        verbose_name_plural = 'Sistemas'
        ordering = ['nombre']
        
    def __str__(self):
        return self.nombre


class Servidor(models.Model):
    """Servidor monitoreado por SNMP."""
    TIPO_CHOICES = [
        ('APP', 'Servidor de Aplicación'),
        ('NETWORK', 'Servidor de Red'),
        ('DB', 'Servidor de Base de Datos'),
        ('SECURITY', 'Servidor de Seguridad'),
        ('OTHER', 'Otros'),
    ]
    
    ESTADO_CHOICES = [
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline'),
    ]

    nombre = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(verbose_name="Dirección IP")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='OTHER')
    sistema_operativo = models.CharField(max_length=100, blank=True)
    
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='OFFLINE')
    last_seen = models.DateTimeField(null=True, blank=True)
    
    # Métricas de Rendimiento (SNMP)
    cpu_usage = models.FloatField(null=True, blank=True, help_text="Porcentaje de uso de CPU")
    memory_total = models.BigIntegerField(null=True, blank=True, help_text="Memoria Total en Bytes")
    memory_used = models.BigIntegerField(null=True, blank=True, help_text="Memoria Usada en Bytes")
    disk_total = models.BigIntegerField(null=True, blank=True, help_text="Disco Total en Bytes")
    disk_used = models.BigIntegerField(null=True, blank=True, help_text="Disco Usado en Bytes")
    uptime = models.CharField(max_length=100, null=True, blank=True, help_text="Tiempo de actividad del sistema")
    
    sistema = models.ForeignKey(Sistema, on_delete=models.CASCADE, related_name='servidores')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Servidor'
        verbose_name_plural = 'Servidores'
        ordering = ['sistema', 'nombre']
        
    def __str__(self):
        return f"{self.nombre} ({self.ip_address})"
