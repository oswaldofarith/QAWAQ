# QAWAQ Deployment Guide

## Prerequisites

- Ubuntu/Debian server with sudo access
- Domain name pointing to server
- Python 3.10+ installed
- PostgreSQL 12+ installed
- Redis installed
- Nginx installed

## Step 1: Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib redis-server git

# Install PostgreSQL development headers
sudo apt install -y libpq-dev

# Start and enable services
sudo systemctl start redis-server postgresql nginx
sudo systemctl enable redis-server postgresql nginx
```

## Step 2: Setup PostgreSQL Database

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL console:
CREATE DATABASE qawaq_db;
CREATE USER qawaq_user WITH PASSWORD 'your_secure_password';
ALTER ROLE qawaq_user SET client_encoding TO 'utf8';
ALTER ROLE qawaq_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE qawaq_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE qawaq_db TO qawaq_user;
\q
```

## Step 3: Setup Application Directory

```bash
# Create application directory
sudo mkdir -p /var/www/qawaq
sudo chown $USER:$USER /var/www/qawaq
cd /var/www/qawaq

# Clone repository
git clone https://github.com/oswaldofarith/QAWAQ.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 4: Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env with production values
nano .env
```

**Required changes in `.env`:**

```bash
# Generate new SECRET_KEY
SECRET_KEY=your-new-secret-key-here

# Production settings
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (update password)
DB_NAME=qawaq_db
DB_USER=qawaq_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1

# Email (configure with your SMTP provider)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your_sendgrid_api_key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

**Generate new SECRET_KEY:**

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Step 5: Run Migrations and Collect Static Files

```bash
# Activate virtual environment
source /var/www/qawaq/venv/bin/activate

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Create backups directory
mkdir -p backups
chmod 700 backups
```

## Step 6: Setup Gunicorn Service

```bash
# Create log directory
sudo mkdir -p /var/log/qawaq
sudo chown www-data:www-data /var/log/qawaq

# Copy systemd service file
sudo cp deploy/systemd/qawaq.service /etc/systemd/system/

# Edit service file if needed
sudo nano /etc/systemd/system/qawaq.service

# Reload systemd
sudo systemctl daemon-reload

# Start and enable service
sudo systemctl start qawaq
sudo systemctl enable qawaq

# Check status
sudo systemctl status qawaq
```

## Step 7: Setup Nginx

```bash
# Copy nginx configuration
sudo cp deploy/nginx/qawaq.conf /etc/nginx/sites-available/qawaq

# Edit configuration with your domain
sudo nano /etc/nginx/sites-available/qawaq

# Create symlink
sudo ln -s /etc/nginx/sites-available/qawaq /etc/nginx/sites-enabled/qawaq

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

## Step 8: Setup SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

## Step 9: Setup Django-Q Worker

```bash
# Create Django-Q systemd service
sudo nano /etc/systemd/system/qawaq-qcluster.service
```

**Content:**

```ini
[Unit]
Description=Django-Q cluster for QAWAQ
After=network.target redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/qawaq
Environment="PATH=/var/www/qawaq/venv/bin"
EnvironmentFile=/var/www/qawaq/.env
ExecStart=/var/www/qawaq/venv/bin/python manage.py qcluster

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start and enable Django-Q
sudo systemctl start qawaq-qcluster
sudo systemctl enable qawaq-qcluster

# Check status
sudo systemctl status qawaq-qcluster
```

## Step 10: Configure Scheduled Tasks

Access Django admin: `https://yourdomain.com/admin`

### Create Backup Task

- Go to: Django Q → Scheduled tasks → Add
- **Name**: Daily Database Backup
- **Func**: `monitor.management.commands.backup_db.Command().handle`
- **Schedule type**: Daily
- **Repeats**: -1 (forever)
- **Time**: 02:00

### Create Alert Task

- **Name**: Equipment Alert Check
- **Func**: `monitor.management.commands.check_equipment_alerts.Command().handle`
- **Schedule type**: Minutes
- **Minutes**: 15
- **Repeats**: -1 (forever)

## Step 11: Configure Administrators

In Django admin, add administrators in `settings.py` or via `.env`:

Edit `/var/www/qawaq/qawaq_project/settings.py`:

```python
ADMINS = [
    ('Admin Name', 'admin@yourdomain.com'),
]
```

Or restart Gunicorn after changing:

```bash
sudo systemctl restart qawaq
```

## Verification Checklist

- [ ] Application accessible via HTTPS
- [ ] HTTP redirects to HTTPS
- [ ] Static files loading correctly
- [ ] Admin panel accessible
- [ ] Django-Q cluster running
- [ ] Redis connection working
- [ ] Database backups running
- [ ] Email alerts configured
- [ ] Logs show no errors

## Monitoring Commands

```bash
# View application logs
sudo journalctl -u qawaq -f

# View Django-Q logs
sudo journalctl -u qawaq-qcluster -f

# View Nginx access logs
sudo tail -f /var/log/nginx/qawaq_access.log

# View Nginx error logs
sudo tail -f /var/log/nginx/qawaq_error.log

# Check application status
sudo systemctl status qawaq qawaq-qcluster nginx redis-server

# Test manual backup
cd /var/www/qawaq
source venv/bin/activate
python manage.py backup_db

# Test alert system
python manage.py check_equipment_alerts
```

## Updating the Application

```bash
# Navigate to application directory
cd /var/www/qawaq

# Activate virtual environment
source venv/bin/activate

# Pull latest changes
git pull origin main

# Install any new dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart qawaq qawaq-qcluster
```

## Troubleshooting

### Gunicorn won't start

```bash
# Check logs
sudo journalctl -u qawaq -n 50

# Test manually
cd /var/www/qawaq
source venv/bin/activate
gunicorn qawaq_project.wsgi:application
```

### Redis connection issues

```bash
# Check Redis status
sudo systemctl status redis-server

# Test Redis
redis-cli ping  # Should return "PONG"
```

### Static files not loading

```bash
# Verify static files collected
ls -l /var/www/qawaq/staticfiles/

# Check Nginx permissions
sudo chown -R www-data:www-data /var/www/qawaq/staticfiles/
```

### SSL certificate issues

```bash
# Renew manually
sudo certbot renew

# Check certificate
sudo certbot certificates
```

## Security Recommendations

1. **Firewall**: Only allow ports 80, 443, and 22

   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

2. **Fail2ban**: Install to prevent brute force attacks

   ```bash
   sudo apt install fail2ban
   ```

3. **Regular updates**: Keep system and packages updated

   ```bash
   sudo apt update && sudo apt upgrade
   ```

4. **Backup offsite**: Consider S3 or similar for backups

5. **Monitor logs**: Regularly check application and system logs

## Support

For issues, check:

- Application logs: `sudo journalctl -u qawaq -f`
- Django-Q logs: `sudo journalctl -u qawaq-qcluster -f`
- Nginx logs: `/var/log/nginx/qawaq_error.log`
