# QAWAQ - Sistema de Monitoreo de Red AMI

Sistema de monitoreo y gestión de equipos de red para infraestructura AMI (Advanced Metering Infrastructure).

## 🎯 Descripción

QAWAQ es una aplicación web para monitorear equipos de red (routers, switches, colectores) en tiempo real, gestionar medidores asociados, y generar reportes de disponibilidad y facturación.

### Características Principales

- ✅ **Monitoreo en Tiempo Real**: Ping automático y detección de equipos offline
- 📊 **Dashboard Interactivo**: Visualización de estado de red con métricas clave
- 🗺️ **Mapa Geográfico**: Ubicación de equipos con Leaflet
- 📅 **Calendario de Facturación**: Gestión de ciclos y eventos de facturación
- 📈 **Reportes**: Individual, masivo y por facturación
- 👥 **Multi-usuario**: Roles de operador y administrador
- 🔔 **Alertas Automáticas**: Notificaciones por email de equipos críticos offline
- 📦 **Importación Masiva**: Excel para equipos, medidores y colectores
- ⚡ **Alta Performance**: Redis cache + índices de base de datos

## 🛠️ Tecnologías

- **Backend**: Django 5.0
- **Base de Datos**: PostgreSQL 12+
- **Cache**: Redis
- **Task Queue**: Django-Q2
- **Frontend**: Bootstrap 5, HTMX
- **Mapas**: Leaflet
- **Servidor**: Nginx + Gunicorn

## 📋 Requisitos

- Python 3.10+
- PostgreSQL 12+
- Redis 6+
- Nginx (producción)

## 🚀 Instalación Rápida (Desarrollo)

### 1. Clonar repositorio

```bash
git clone https://github.com/oswaldofarith/QAWAQ.git
cd QAWAQ
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus valores
```

Generar SECRET_KEY:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Configurar base de datos

```sql
-- En PostgreSQL
CREATE DATABASE qawaq_db;
CREATE USER qawaq_user WITH PASSWORD 'tu_password';
GRANT ALL PRIVILEGES ON DATABASE qawaq_db TO qawaq_user;
```

### 6. Ejecutar migraciones

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 7. Iniciar servicios

```bash
# Terminal 1: Django-Q worker
python manage.py qcluster

# Terminal 2: Servidor de desarrollo
python manage.py runserver
```

Visitar: <http://localhost:8000>

## 🌐 Deployment a Producción

Ver guía completa en [`deploy/DEPLOYMENT.md`](deploy/DEPLOYMENT.md)

### Quick Start Producción

```bash
# 1. Instalar dependencias del sistema
sudo apt install postgresql redis-server nginx

# 2. Seguir pasos 1-6 de arriba

# 3. Configurar servicios
sudo cp deploy/systemd/qawaq.service /etc/systemd/system/
sudo cp deploy/nginx/qawaq.conf /etc/nginx/sites-available/qawaq

# 4. SSL con Let's Encrypt
sudo certbot --nginx -d tudominio.com

# 5. Iniciar servicios
sudo systemctl start qawaq qawaq-qcluster
sudo systemctl enable qawaq qawaq-qcluster
```

## 📚 Comandos Útiles

### Gestión

```bash
# Backup de base de datos
python manage.py backup_db

# Verificar equipos críticos offline
python manage.py check_equipment_alerts

# Estadísticas de base de datos
python manage.py db_stats --table-stats
```

### Desarrollo

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Recolectar archivos estáticos
python manage.py collectstatic

# Shell interactivo
python manage.py shell
```

## 🏗️ Estructura del Proyecto

```
QAWAQ/
├── monitor/              # App principal
│   ├── models.py        # Modelos: Equipo, Medidor, etc.
│   ├── views/           # Vistas separadas por funcionalidad
│   ├── forms.py         # Formularios
│   ├── templates/       # Templates HTML
│   ├── management/      # Comandos custom
│   └── services/        # Lógica de negocio (alertas, etc.)
├── qawaq_project/       # Configuración Django
│   ├── settings.py      # Settings principal
│   └── urls.py          # URLs raíz
├── templates/           # Templates base
├── static/              # Archivos estáticos
├── deploy/              # Configuraciones de deployment
│   ├── nginx/          # Config Nginx
│   ├── systemd/        # Servicios systemd
│   ├── DEPLOYMENT.md   # Guía de deployment
│   └── POSTGRES_OPTIMIZATION.md  # Optimización DB
└── requirements.txt     # Dependencias Python
```

## 🔒 Seguridad

- Variables de entorno para credenciales (no en código)
- SSL/HTTPS obligatorio en producción
- Headers de seguridad configurados
- Validación de archivos subidos
- Rate limiting recomendado (Nginx)

## 📊 Monitoreo

- **Sentry**: Tracking de errores (configurar SENTRY_DSN)
- **Health Checks**: `/health/`, `/health/ready/`, `/health/live/`
- **Logs**: Logs rotativos en `/var/log/qawaq/`
- **Django-Q**: Monitor de tareas asíncronas

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrir Pull Request

## 📝 Licencia

Proyecto privado - Todos los derechos reservados

## 👥 Autores

- Oswaldo Farith ([oswaldofarith](https://github.com/oswaldofarith))

## 🆘 Soporte

Para problemas o preguntas:

1. Ver [DEPLOYMENT.md](deploy/DEPLOYMENT.md) y [POSTGRES_OPTIMIZATION.md](deploy/POSTGRES_OPTIMIZATION.md)
2. Revisar logs: `sudo journalctl -u qawaq -f`
3. Abrir issue en GitHub

## 🎯 Roadmap

- [ ] API REST para integración externa
- [ ] Notificaciones push en tiempo real
- [ ] Dashboard móvil
- [ ] Reportes programados automáticos
- [ ] Integración con sistemas de ticketing

---

**QAWAQ Vigilante AMI** - Sistema de Monitoreo de Red © 2026
