# PostgreSQL Performance Optimization Settings

## Database Configuration for Production

Add these settings to your PostgreSQL configuration file (`postgresql.conf`):

### 1. Enable Query Statistics

```sql
-- In postgresql.conf or via ALTER SYSTEM
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.max = 10000
pg_stat_statements.track = all
```

**Restart PostgreSQL after changing `shared_preload_libraries`:**

```bash
sudo systemctl restart postgresql
```

### 2. Create Extension

Connect to your database and enable the extension:

```sql
-- Connect to qawaq_db
psql -U qawaq_user -d qawaq_db

-- Enable extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

### 3. Configure Connection Pool Settings

In `postgresql.conf`:

```ini
# Connection Settings
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

**Note:** Adjust values based on your server's RAM. Rule of thumb:

- `shared_buffers`: 25% of total RAM
- `effective_cache_size`: 50-75% of total RAM

## Monitoring Slow Queries

### View Top 10 Slowest Queries

```sql
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### View Most Frequently Called Queries

```sql
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 10;
```

### Reset Statistics

```sql
SELECT pg_stat_statements_reset();
```

## Index Verification

Check if indexes are being used:

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

## QAWAQ Specific Queries for Monitoring

### 1. Check Equipment Query Performance

```sql
-- Before optimization
EXPLAIN ANALYZE
SELECT * FROM monitor_equipo
WHERE is_online = true
ORDER BY last_seen DESC;

-- Should now use index: monitor_equ_online_time_idx
```

### 2. Check Billing Events Performance

```sql
-- Before optimization
EXPLAIN ANALYZE
SELECT * FROM monitor_eventofacturacion
WHERE fecha >= '2026-01-01' AND fecha <= '2026-01-31'
  AND tipo_evento = 'FACTURACION';

-- Should now use index: monitor_evt_fecha_tipo_idx
```

### 3. Check Medidor Lookup Performance

```sql
-- Before optimization
EXPLAIN ANALYZE
SELECT * FROM monitor_medidor
WHERE id_medidor = 'MED-12345';

-- Should now use index: monitor_med_id_medi_idx
```

## Table Statistics

Update table statistics for better query planning:

```sql
-- After adding indexes or bulk inserts
ANALYZE monitor_equipo;
ANALYZE monitor_medidor;
ANALYZE monitor_eventofacturacion;
ANALYZE monitor_historial_disponibilidad;
```

## Vacuum Full (Maintenance)

Run periodically to reclaim space and update statistics:

```sql
-- Manual vacuum (run during low-traffic hours)
VACUUM FULL ANALYZE monitor_equipo;
VACUUM FULL ANALYZE monitor_medidor;
VACUUM FULL ANALYZE monitor_historial_disponibilidad;
```

**Better:** Enable autovacuum in postgresql.conf:

```ini
autovacuum = on
autovacuum_vacuum_scale_factor = 0.1
autovacuum_analyze_scale_factor = 0.05
```

## Django Settings for Connection Pooling

Add to `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'OPTIONS': {
            'client_encoding': 'UTF8',
        },
        'CONN_MAX_AGE': 600,  # Keep connections alive for 10 minutes
        'ATOMIC_REQUESTS': True,  # Wrap requests in transactions
    }
}
```

## Regular Maintenance Schedule

Create a cron job for maintenance (run weekly):

```bash
# /etc/cron.weekly/postgresql-maintenance
#!/bin/bash
sudo -u postgres psql qawaq_db -c "VACUUM ANALYZE;"
```

## Performance Testing After Index Creation

Run these commands to verify improvement:

```bash
# 1. Apply migration
python manage.py migrate

# 2. Test query performance in Django shell
python manage.py shell
```

```python
from django.db import connection
from django.db import reset_queries
from django.conf import settings
settings.DEBUG = True  # Enable query logging

from monitor.models import Equipo, EventoFacturacion

# Test 1: Online equipment query
reset_queries()
list(Equipo.objects.filter(is_online=True).order_by('-last_seen')[:100])
print(f"Queries: {len(connection.queries)}")
print(f"Time: {sum(float(q['time']) for q in connection.queries):.3f}s")

# Test 2: Billing events query
reset_queries()
from datetime import date
events = list(EventoFacturacion.objects.filter(
    fecha__gte=date(2026, 1, 1),
    fecha__lte=date(2026, 1, 31),
    tipo_evento='FACTURACION'
))
print(f"Queries: {len(connection.queries)}")
print(f"Time: {sum(float(q['time']) for q in connection.queries):.3f}s")
```

## Expected Performance Improvements

With the added indexes, you should see:

- **Equipment queries**: 70-90% faster (especially filtered by `is_online` or `last_seen`)
- **Billing reports**: 60-80% faster (filtered by `fecha` and `tipo_evento`)
- **Medidor lookups**: 80-95% faster (by `id_medidor`)
- **Dashboard loading**: 50-70% faster (combined effect)

## Monitoring Tools

### pgAdmin

- Visual query analyzer
- Index usage statistics
- Connection pool monitoring

### pg_top / pg_activity

```bash
sudo apt install pgtop
pg_top -U postgres
```

### Datadog / New Relic

For production monitoring (paid services)
