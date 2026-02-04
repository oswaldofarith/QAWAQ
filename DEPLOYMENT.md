# Guía de Despliegue en Producción - QAWAQ

**Sistema Operativo:** Ubuntu 24.04 LTS
**Stack:** Django + Gunicorn + Nginx + PostgreSQL + Redis + Django Q

## 1. Preparación del Servidor

Actualizar el sistema e instalar dependencias base:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx redis-server git curl pkg-config libcairo2-dev libjpeg-dev libgif-dev
```

Habilitar y arrancar Redis:

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

## 2. Configuración de Base de Datos (PostgreSQL)

Acceder a la consola de Postgres:

```bash
sudo -u postgres psql
```

Ejecutar las siguientes consultas (cambia la contraseña por una segura):

```sql
CREATE DATABASE qawaq_db;
CREATE USER qawaq_man WITH PASSWORD 'TuPasswordSeguro123';
ALTER ROLE qawaq_man SET client_encoding TO 'utf8';
ALTER ROLE qawaq_man SET default_transaction_isolation TO 'read committed';
ALTER ROLE qawaq_man SET timezone TO 'America/Guayaquil';
GRANT ALL PRIVILEGES ON DATABASE qawaq_db TO qawaq_man;
-- Para PostgreSQL 15+ es necesario dar permisos explícitos sobre el esquema public
\c qawaq_db
GRANT ALL ON SCHEMA public TO qawaq_man;
\q
```

## 3. Configuración del Proyecto

Recomendamos instalar la aplicación en `/var/www/qawaq`.

### 3.1. Clonar Repositorio y Entorno Virtual

```bash
# Crear directorio y asignar permisos (ajusta 'usuario' a tu usuario actual)
sudo mkdir -p /var/www/qawaq
sudo chown -R $USER:$USER /var/www/qawaq

cd /var/www/qawaq
git clone <URL_DEL_REPOSITORIO> .

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
pip install gunicorn
```

### 3.2. Configurar Variables de Entorno (.env)

Crear el archivo `.env` en la raíz del proyecto (`/var/www/qawaq/`):

```bash
nano .env
```

Contenido recomendado:

```ini
DEBUG=False
SECRET_KEY=GenerarUnaClaveLargaYUnicaAqui
ALLOWED_HOSTS=midominio.com,IP_DEL_SERVIDOR

# Base de Datos
DB_NAME=qawaq_db
DB_USER=qawaq_man
DB_PASSWORD=TuPasswordSeguro123
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1

# Configuración de Correo (Ejemplo Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu@email.com
EMAIL_HOST_PASSWORD=tu_app_password
```

### 3.3. Preparar Django

```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
python manage.py createsuperuser

# Generar Licencia (Necesario para acceder al sistema)
python manage.py shell -c "from monitor.services.license_service import LicenseService; token = LicenseService.generate_license(client_name='Production', days_valid=3650, email='admin@qawaq.com'); LicenseService.save_license_file(token); print('Licencia generada correctamente')"
```

## 4. Configurar Gunicorn (Servidor de Aplicación)

Crear archivo de servicio systemd:
`sudo nano /etc/systemd/system/qawaq.service`

```ini
[Unit]
Description=gunicorn daemon for QAWAQ
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/qawaq
ExecStart=/var/www/qawaq/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/var/www/qawaq/qawaq.sock \
          qawaq_project.wsgi:application

[Install]
WantedBy=multi-user.target
```

## 5. Configurar Django Q (Cluster de Tareas)

Crear archivo de servicio systemd:
`sudo nano /etc/systemd/system/qawaq-qcluster.service`

```ini
[Unit]
Description=Django Q Cluster for QAWAQ
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/qawaq
ExecStart=/var/www/qawaq/venv/bin/python manage.py qcluster
Restart=always

[Install]
WantedBy=multi-user.target
```

## 6. Permisos y Arranque de Servicios

```bash
# Cambiar propietario a www-data (usuario de Nginx/Gunicorn)
sudo chown -R www-data:www-data /var/www/qawaq

# Iniciar servicios
sudo systemctl start qawaq
sudo systemctl enable qawaq
sudo systemctl start qawaq-qcluster
sudo systemctl enable qawaq-qcluster
```

## 7. Configurar Nginx (Servidor Web)

Crear configuración del sitio:
`sudo nano /etc/nginx/sites-available/qawaq`

```nginx
server {
    listen 80;
    server_name midominio.com IP_DEL_SERVIDOR;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    # Archivos Estáticos
    location /static/ {
        root /var/www/qawaq; # Nginx buscará en /var/www/qawaq/static/
    }

    # Archivos Media (Subidos por usuarios)
    location /media/ {
        root /var/www/qawaq;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/qawaq/qawaq.sock;
    }
}
```

Habilitar el sitio:

```bash
sudo ln -s /etc/nginx/sites-available/qawaq /etc/nginx/sites-enabled/
sudo nginx -t  # Verificar sintaxis
sudo systemctl restart nginx
```

## 8. Seguridad HTTPS (Certbot)

Si tienes un dominio configurado:

```bash
sudo apt install python3-certbot-nginx
sudo certbot --nginx -d midominio.com
```

## 9. Comandos Útiles de Mantenimiento

**Ver logs:**

```bash
sudo journalctl -u qawaq -f          # Logs de Django/Gunicorn
sudo journalctl -u qawaq-qcluster -f # Logs de Tareas (Django Q)
sudo tail -f /var/log/nginx/error.log # Logs de Nginx
```

**Desplegar cambios:**

```bash
cd /var/www/qawaq
git pull
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart qawaq
sudo systemctl restart qawaq-qcluster
```
