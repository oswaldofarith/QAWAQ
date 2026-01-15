# QAWAQ Health Check Endpoints

Los health check endpoints están implementados y listos para usar en producción.

## Endpoints Disponibles

### 1. `/health/` - Health Check Completo

**URL:** `http://localhost:8000/health/` (desarrollo) o `https://tudominio.com/health/` (producción)

**Verifica:**

- ✅ Conexión a PostgreSQL
- ✅ Conexión a Redis

**Respuesta Exitosa (200 OK):**

```json
{
  "status": "healthy",
  "timestamp": "2026-01-15T16:17:30.123456",
  "checks": {
    "database": true,
    "cache": true
  }
}
```

**Respuesta Fallida (503 Service Unavailable):**

```json
{
  "status": "unhealthy",
  "timestamp": "2026-01-15T16:17:30.123456",
  "checks": {
    "database": true,
    "cache": false
  }
}
```

**Uso:**

```bash
curl http://localhost:8000/health/
```

---

### 2. `/health/ready/` - Readiness Check

**Propósito:** Para Kubernetes/Docker - indica si la aplicación está lista para recibir tráfico

**Respuesta:**

```json
{
  "status": "ready"
}
```

**Status Code:** 200 OK

**Uso en Kubernetes:**

```yaml
readinessProbe:
  httpGet:
    path: /health/ready/
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

---

### 3. `/health/live/` - Liveness Check

**Propósito:** Para Kubernetes/Docker - indica si el proceso de la aplicación está vivo

**Respuesta:**

```json
{
  "status": "alive"
}
```

**Status Code:** 200 OK

**Uso en Kubernetes:**

```yaml
livenessProbe:
  httpGet:
    path: /health/live/
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 20
```

---

## Testing Local

### Método 1: curl

```bash
# Health check completo
curl http://localhost:8000/health/

# Readiness
curl http://localhost:8000/health/ready/

# Liveness
curl http://localhost:8000/health/live/
```

### Método 2: Navegador

Visita en tu navegador:

- <http://localhost:8000/health/>
- <http://localhost:8000/health/ready/>
- <http://localhost:8000/health/live/>

### Método 3: Python requests

```python
import requests

response = requests.get('http://localhost:8000/health/')
print(f"Status: {response.status_code}")
print(f"Body: {response.json()}")
```

---

## Configuración en Producción

### Nginx Upstream Health Check

```nginx
upstream backend {
    server 127.0.0.1:8000;
    
    # Health check (requiere nginx-plus o módulo community)
    check interval=5000 rise=2 fall=3 timeout=1000 type=http;
    check_http_send "GET /health/ HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx;
}
```

### Monitoreo Externo (UptimeRobot, Pingdom)

**Configuración recomendada:**

- **URL:** `https://tudominio.com/health/`
- **Método:** GET
- **Intervalo:** 5 minutos
- **Alerta si:** Status code ≠ 200
- **Timeout:** 30 segundos

### Docker Compose

```yaml
services:
  web:
    image: qawaq:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qawaq
spec:
  template:
    spec:
      containers:
      - name: qawaq
        image: qawaq:latest
        ports:
        - containerPort: 8000
        
        # Liveness probe
        livenessProbe:
          httpGet:
            path: /health/live/
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 20
          timeoutSeconds: 5
          failureThreshold: 3
        
        # Readiness probe
        readinessProbe:
          httpGet:
            path: /health/ready/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
```

---

## Troubleshooting

### Health check retorna "unhealthy"

**Verificar base de datos:**

```bash
# Conectar a PostgreSQL
psql -U qawaq_user -d qawaq_db -c "SELECT 1"
```

**Verificar Redis:**

```bash
# Test Redis
redis-cli ping
# Debería retornar: PONG
```

### Health check no responde (timeout)

**Verificar que Django está corriendo:**

```bash
# Ver logs
sudo journalctl -u qawaq -n 50

# O si estás usando runserver
# Revisar consola donde corre el servidor
```

**Verificar firewall:**

```bash
# Permitir puerto 8000 (desarrollo)
sudo ufw allow 8000/tcp
```

### Health check retorna 404

**Verificar URLs:**

```bash
python manage.py show_urls | grep health
```

Deberías ver:

```
/health/        monitor:health_check
/health/ready/  monitor:readiness_check
/health/live/   monitor:liveness_check
```

---

## Logs

Los health checks logean errores automáticamente:

```python
# En monitor/views/health.py
logger.error(f"Database health check failed: {e}")
logger.error(f"Cache health check failed: {e}")
```

**Ver logs:**

```bash
# Desarrollo
# Los errores aparecen en la consola del runserver

# Producción
sudo journalctl -u qawaq | grep "health check"
```

---

## Métricas Recomendadas

### Prometheus

Aunque actualmente no está implementado, puedes agregar métricas de Prometheus:

```python
# Futuro: agregar prometheus_client
from prometheus_client import Counter, Histogram

health_check_total = Counter('health_check_total', 'Total health checks')
health_check_failures = Counter('health_check_failures', 'Failed health checks')
health_check_duration = Histogram('health_check_duration_seconds', 'Health check duration')
```

---

## Resumen

✅ **3 endpoints implementados** (`/health/`, `/health/ready/`, `/health/live/`)  
✅ **Verificación de DB y Redis** en health check completo  
✅ **Status codes apropiados** (200 healthy, 503 unhealthy)  
✅ **Logging de errores** automático  
✅ **Compatible con K8s**, Docker, y load balancers  

**Próximo paso:** Configurar monitoreo externo o integrar con tu orquestador (K8s/Docker).
