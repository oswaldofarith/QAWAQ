# Redis Installation and Testing Guide

## Windows Development

For development on Windows, you can use Redis in several ways:

### Option 1: WSL2 (Recommended)

```bash
# In WSL2 Ubuntu
sudo apt update
sudo apt install redis-server

# Start Redis
sudo service redis-server start

# Test connection
redis-cli ping  # Should return "PONG"
```

### Option 2: Docker (Alternative)

```bash
# Run Redis in Docker
docker run -d -p 6379:6379 --name redis-qawaq redis:latest

# Test connection
docker exec -it redis-qawaq redis-cli ping
```

### Option 3: Windows Native (via Memurai)

Download and install Memurai from: <https://www.memurai.com/>

## Testing Redis Cache in QAWAQ

### 1. Verify Redis Connection

```bash
# Test from Django shell
python manage.py shell
```

```python
from django.core.cache import cache

# Set a value
cache.set('test_key', 'Hello Redis!', timeout=60)

# Get the value
print(cache.get('test_key'))  # Should print: Hello Redis!

# Delete
cache.delete('test_key')
```

### 2. Check Session Storage

After configuring `SESSION_ENGINE = 'django.contrib.sessions.backends.cache'`:

1. Login to the application
2. Check Redis for session data:

```bash
redis-cli
> KEYS qawaq:*
```

Should show session keys like `qawaq:1:django.contrib.sessions.cache...`

### 3. Monitor Redis Activity

```bash
# Real-time monitoring
redis-cli MONITOR

# Stats
redis-cli INFO stats
```

## Production Setup

See [DEPLOYMENT.md](file:///g:/Mi%20unidad/Dev/QAWAQ/deploy/DEPLOYMENT.md) for production Redis configuration.

### Quick Redis Configuration Check

```bash
# Memory usage
redis-cli INFO memory

# Number of keys
redis-cli DBSIZE

# Flush all keys (CAUTION: only in development)
redis-cli FLUSHALL
```

## Performance Tips

1. **Monitor memory**: Redis stores data in RAM
2. **Set maxmemory**: Configure in redis.conf
3. **Use appropriate timeouts**: Balance between performance and freshness
4. **Monitor hit rate**: Check cache effectiveness

## Common Redis Commands

```bash
# Check connected clients
redis-cli CLIENT LIST

# Get configuration
redis-cli CONFIG GET maxmemory

# Set configuration
redis-cli CONFIG SET maxmemory 256mb

# Backup
redis-cli SAVE
```
