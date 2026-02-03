from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import (
    UserProfile, ConfiguracionGlobal, Marca, TipoEquipo, Equipo,
    Porcion, CicloFacturacion, EventoFacturacion, Sistema, Servidor
)
import re


class EquipoImportForm(forms.Form):
    """Form for importing equipment from XLSX files."""
    
    DUPLICATE_CHOICES = [
        ('skip', 'Omitir equipos duplicados (mantener datos existentes)'),
        ('update', 'Actualizar equipos existentes (fusionar datos)'),
    ]
    
    archivo_xlsx = forms.FileField(
        label='Archivo XLSX',
        help_text='Seleccione un archivo Excel (.xlsx) con los datos de equipos. Máximo 5MB.',
        widget=forms.FileInput(attrs={
            'accept': '.xlsx',
            'class': 'form-control'
        })
    )
    
    duplicate_action = forms.ChoiceField(
        choices=DUPLICATE_CHOICES,
        initial='skip',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Acción para equipos duplicados',
        required=False,
        help_text='Los campos vacíos en el archivo no sobrescribirán datos existentes al actualizar'
    )
    
    def clean_archivo_xlsx(self):
        archivo = self.cleaned_data.get('archivo_xlsx')
        
        if not archivo:
            raise ValidationError('Por favor seleccione un archivo.')
        
        # Validate file extension
        if not archivo.name.endswith('.xlsx'):
            raise ValidationError('El archivo debe ser de tipo .xlsx (Excel).')
        
        # Validate file size (5MB max)
        max_size = 5 * 1024 * 1024  # 5MB in bytes
        if archivo.size > max_size:
            raise ValidationError(
                f'El archivo es muy grande ({archivo.size / (1024*1024):.2f}MB). '
                f'Máximo permitido: 5MB.'
            )
        
        return archivo


class UserProfileForm(forms.ModelForm):
    """Form for creating and editing user profiles."""
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Nombre de Usuario'
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Nombre'
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Apellido'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label='Correo Electrónico'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        label='Contraseña',
        help_text='Dejar en blanco para mantener la contraseña actual'
    )
    
    class Meta:
        model = UserProfile
        fields = ['role', 'avatar']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Editing existing user
            self.fields['username'].initial = self.instance.user.username
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # Create or update User
        if profile.pk:
            # Update existing user
            profile.user.username = self.cleaned_data['username']
            profile.user.first_name = self.cleaned_data['first_name']
            profile.user.last_name = self.cleaned_data['last_name']
            profile.user.email = self.cleaned_data['email']
            
            if self.cleaned_data.get('password'):
                profile.user.set_password(self.cleaned_data['password'])
            
            if commit:
                profile.user.save()
                profile.save()
        else:
            # Create new user - signal will create profile automatically
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                email=self.cleaned_data['email'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                password=self.cleaned_data.get('password', 'changeme123')
            )
            # Get the profile created by the signal
            profile = user.profile
            # Update profile fields from form
            profile.role = self.cleaned_data.get('role', 'operator')
            if self.cleaned_data.get('avatar'):
                profile.avatar = self.cleaned_data['avatar']
            if commit:
                profile.save()
        
        return profile


class ConfiguracionGlobalForm(forms.ModelForm):
    """Form for editing global system configuration."""
    
    class Meta:
        model = ConfiguracionGlobal
        fields = ['tiempo_interrogacion', 'reintentos', 'umbral_falla_fibra', 'umbral_falla_celular']
        widgets = {
            'tiempo_interrogacion': forms.NumberInput(attrs={'class': 'form-control', 'min': '10'}),
            'reintentos': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'umbral_falla_fibra': forms.NumberInput(attrs={'class': 'form-control', 'min': '30'}),
            'umbral_falla_celular': forms.NumberInput(attrs={'class': 'form-control', 'min': '60'}),
        }
        labels = {
            'tiempo_interrogacion': 'Tiempo entre Pings (segundos)',
            'reintentos': 'Número de Reintentos',
            'umbral_falla_fibra': 'Umbral Falla Fibra (segundos)',
            'umbral_falla_celular': 'Umbral Falla Celular (segundos)',
        }
    
    def clean_tiempo_interrogacion(self):
        value = self.cleaned_data['tiempo_interrogacion']
        if value < 10:
            raise ValidationError('El tiempo mínimo es 10 segundos.')
        return value
    
    def clean_umbral_falla_fibra(self):
        value = self.cleaned_data['umbral_falla_fibra']
        if value < 30:
            raise ValidationError('El umbral mínimo para fibra es 30 segundos.')
        return value
    
    def clean_umbral_falla_celular(self):
        value = self.cleaned_data['umbral_falla_celular']
        if value < 60:
            raise ValidationError('El umbral mínimo para celular es 60 segundos.')
        return value


class MarcaForm(forms.ModelForm):
    """Form for creating/editing equipment brands."""
    
    class Meta:
        model = Marca
        fields = ['nombre', 'color']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ej: Cisco'}),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'style': 'width: 80px; height: 40px;'
            }),
        }
        labels = {
            'nombre': 'Nombre de la Marca',
            'color': 'Color de Identificación',
        }


class TipoEquipoForm(forms.ModelForm):
    """Form for creating/editing equipment types."""
    
    class Meta:
        model = TipoEquipo
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ej: Router'}),
        }
        labels = {
            'nombre': 'Nombre del Tipo',
        }


import re
from django.core.exceptions import ValidationError


class EquipoForm(forms.ModelForm):
    """Form for creating and editing equipment."""
    
    class Meta:
        model = Equipo
        fields = [
            'id_equipo', 'ip', 'marca', 'tipo', 'estado', 'piloto',
            'medio_comunicacion', 'latitud', 'longitud', 'direccion', 'poste'
        ]
        widgets = {
            'id_equipo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ej: EQ-001'}),
            'ip': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ej: 192.168.1.100'}),
            'marca': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'piloto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ej: Juan Pérez'}),
            'medio_comunicacion': forms.Select(attrs={'class': 'form-select'}),
            'latitud': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': 'ej: -12.046374'}),
            'longitud': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': 'ej: -77.042793'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Dirección física del equipo'}),
            'poste': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ej: P-123'}),
        }
        labels = {
            'id_equipo': 'ID del Equipo',
            'ip': 'Dirección IP',
            'marca': 'Marca',
            'tipo': 'Tipo de Equipo',
            'estado': 'Estado',
            'piloto': 'Piloto',
            'medio_comunicacion': 'Medio de Comunicación',
            'latitud': 'Latitud',
            'longitud': 'Longitud',
            'direccion': 'Dirección Física',
            'poste': 'Poste',
        }
    
    def clean_ip(self):
        """Validate IP address format and uniqueness."""
        ip = self.cleaned_data.get('ip')
        
        # Validate IP format (simple IPv4 regex)
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, ip):
            raise ValidationError('Formato de IP inválido. Use formato IPv4 (ej: 192.168.1.1)')
        
        # Validate each octet is 0-255
        octets = ip.split('.')
        for octet in octets:
            if int(octet) > 255:
                raise ValidationError('Cada octeto debe estar entre 0 y 255.')
        
        # Check uniqueness (exclude current instance if editing)
        queryset = Equipo.objects.filter(ip=ip)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError(f'Ya existe un equipo con la IP "{ip}".')
        
        return ip
    
    def clean_id_equipo(self):
        """Validate equipment ID uniqueness."""
        id_equipo = self.cleaned_data.get('id_equipo')
        
        # Check uniqueness (exclude current instance if editing)
        queryset = Equipo.objects.filter(id_equipo=id_equipo)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError(f'Ya existe un equipo con el ID "{id_equipo}".')
        
        return id_equipo
    
    def clean(self):
        """Validate coordinates together."""
        cleaned_data = super().clean()
        latitud = cleaned_data.get('latitud')
        longitud = cleaned_data.get('longitud')
        
        # If one coordinate is provided, both must be provided
        if (latitud is not None and longitud is None) or (latitud is None and longitud is not None):
            raise ValidationError('Si proporciona coordenadas, debe proporcionar tanto latitud como longitud.')
        
        # Validate coordinate ranges
        if latitud is not None:
            if latitud < -90 or latitud > 90:
                self.add_error('latitud', 'La latitud debe estar entre -90 y 90.')
        
        if longitud is not None:
            if longitud < -180 or longitud > 180:
                self.add_error('longitud', 'La longitud debe estar entre -180 y 180.')
        
        return cleaned_data


class PasswordChangeForm(forms.Form):
    """Form for changing user password."""
    
    current_password = forms.CharField(
        label='Contraseña Actual',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu contraseña actual'
        }),
        required=True
    )
    new_password1 = forms.CharField(
        label='Nueva Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo 8 caracteres'
        }),
        required=True,
        help_text='La contraseña debe tener al menos 8 caracteres'
    )
    new_password2 = forms.CharField(
        label='Confirmar Nueva Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repite la nueva contraseña'
        }),
        required=True
    )
    
    def __init__(self, user, *args, **kwargs):
        """Initialize form with the current user."""
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        """Verify that the current password is correct."""
        current = self.cleaned_data.get('current_password')
        if not self.user.check_password(current):
            raise ValidationError('La contraseña actual es incorrecta.')
        return current
    
    def clean(self):
        """Verify new passwords match and meet requirements."""
        cleaned_data = super().clean()
        new1 = cleaned_data.get('new_password1')
        new2 = cleaned_data.get('new_password2')
        
        if new1 and new2:
            # Check passwords match
            if new1 != new2:
                raise ValidationError('Las contraseñas nuevas no coinciden.')
            
            # Minimum length check
            if len(new1) < 8:
                raise ValidationError('La contraseña debe tener al menos 8 caracteres.')
            
            # Check not same as current
            if self.user.check_password(new1):
                raise ValidationError('La nueva contraseña debe ser diferente a la actual.')
        
        return cleaned_data
    
    def save(self):
        """Update the user's password."""
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        self.user.save()
        return self.user


class MyProfileForm(forms.ModelForm):
    """Form for users to edit their own profile."""
    
    first_name = forms.CharField(
        max_length=150,
        required=False,
        label='Nombre',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu nombre'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label='Apellido',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu apellido'
        })
    )
    email = forms.EmailField(
        required=True,
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'tu@email.com'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ['avatar', 'telegram_chat_id', 'email_notifications', 'telegram_notifications']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'telegram_chat_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '123456789'
            }),
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'telegram_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'avatar': 'Foto de Perfil',
            'telegram_chat_id': 'Chat ID de Telegram',
            'email_notifications': 'Notificaciones por Email',
            'telegram_notifications': 'Notificaciones por Telegram'
        }
        help_texts = {
            'telegram_chat_id': 'Para obtener tu Chat ID, habla con @userinfobot en Telegram',
            'email_notifications': 'Recibir alertas de equipos críticos por correo electrónico',
            'telegram_notifications': 'Recibir alertas de equipos críticos por Telegram (requiere Chat ID)'
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form with User data."""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
    
    def clean_email(self):
        """Validate email uniqueness (excluding current user)."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise ValidationError('Este correo electrónico ya está en uso por otro usuario.')
        return email
    
    def save(self, commit=True):
        """Save both User and UserProfile."""
        profile = super().save(commit=False)
        
        # Update User fields
        self.user.first_name = self.cleaned_data.get('first_name', '')
        self.user.last_name = self.cleaned_data.get('last_name', '')
        self.user.email = self.cleaned_data.get('email', '')
        
        if commit:
            self.user.save()
            profile.save()
        
        return profile


class PorcionForm(forms.ModelForm):
    """Form for creating and editing customer portions."""
    
    class Meta:
        model = Porcion
        fields = ['nombre', 'tipo', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ej: 401i'
            }),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la porción'
            }),
        }
        labels = {
            'nombre': 'Nombre',
            'tipo': 'Tipo de Porción',
            'descripcion': 'Descripción',
        }


class EventoFacturacionForm(forms.ModelForm):
    """Form for creating and editing billing events."""
    
    class Meta:
        model = EventoFacturacion
        fields = ['porcion', 'tipo_evento', 'fecha']
        widgets = {
            'porcion': forms.Select(attrs={'class': 'form-select'}),
            'tipo_evento': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'porcion': 'Porción',
            'tipo_evento': 'Tipo de Evento',
            'fecha': 'Fecha',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default tipo_evento to FACTURACION for new events
        if not self.instance.pk:
            self.fields['tipo_evento'].initial = 'FACTURACION'
        else:
            # When editing, format the date for HTML5 date input (YYYY-MM-DD)
            if self.instance.fecha:
                self.fields['fecha'].initial = self.instance.fecha.strftime('%Y-%m-%d')
    
    def clean(self):
        """Validate and auto-create billing cycle if needed."""
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        porcion = cleaned_data.get('porcion')
        
        if fecha and porcion:
            # Get or create the appropriate billing cycle
            mes = fecha.month
            anio = fecha.year
            tipo_ciclo = porcion.tipo
            
            ciclo, created = CicloFacturacion.objects.get_or_create(
                mes=mes,
                anio=anio,
                tipo=tipo_ciclo
            )
            cleaned_data['ciclo'] = ciclo
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save with the auto-created billing cycle."""
        instance = super().save(commit=False)
        instance.ciclo = self.cleaned_data['ciclo']
        
        if commit:
            instance.save()
        
        return instance


class SistemaForm(forms.ModelForm):
    """Form for creating and editing systems."""
    class Meta:
        model = Sistema
        fields = ['nombre', 'marca', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Sistema (ej: HES Trilliant)'}),
            'marca': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'nombre': 'Nombre',
            'marca': 'Marca',
            'descripcion': 'Descripción',
        }

class ServidorForm(forms.ModelForm):
    """Form for creating and editing servers."""
    class Meta:
        model = Servidor
        fields = ['nombre', 'ip_address', 'tipo', 'sistema_operativo', 'sistema']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Servidor'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '192.168.x.x'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'sistema_operativo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ej: Windows Server 2022'}),
            'sistema': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'nombre': 'Nombre',
            'ip_address': 'Dirección IP',
            'tipo': 'Tipo de Servidor',
            'sistema_operativo': 'Sistema Operativo',
            'sistema': 'Sistema al que pertenece',
        }
