from django_q.tasks import async_task
from django.utils import timezone
from .models import Equipo, HistorialDisponibilidad, ConfiguracionGlobal
import logging
import subprocess
import platform
import re
import math

logger = logging.getLogger(__name__)

def ping_host(host, timeout=1):
    os_name = platform.system().lower()
    # Timeout in milliseconds for Windows, seconds for Linux
    if 'windows' in os_name:
        cmd = ['ping', '-n', '1', '-w', str(int(timeout*1000)), host]
    else:
        cmd = ['ping', '-c', '1', '-W', str(int(timeout)), host]
        
    try:
        # Use subprocess to ping
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            # Parse output for time
            # Windows: "time=3ms" or "tiempo=3ms"
            # Linux: "time=3.4 ms"
            match = re.search(r'time[=<](\d+[\.]?\d*) ?ms', result.stdout, re.IGNORECASE)
            # Some spanish windows versions use "tiempo="
            if not match:
                match = re.search(r'tiempo[=<](\d+[\.]?\d*) ?ms', result.stdout, re.IGNORECASE)
                
            if match:
                return float(match.group(1))
            return 1.0 # Default if success but parse fail (very low latency)
        return None
    except Exception as e:
        logger.error(f"Error pinging {host}: {e}")
        return None

def check_device(device_id):
    try:
        device = Equipo.objects.get(id=device_id)
    except Equipo.DoesNotExist:
        return

    if device.estado == 'INACTIVO' or device.en_mantenimiento:
        return

    config = ConfiguracionGlobal.load()
    
    # Try ping
    latency = ping_host(device.ip, timeout=2) # Default 2s timeout
    
    # Logic for retries if failed
    if latency is None and config.reintentos > 0:
        for _ in range(config.reintentos):
            latency = ping_host(device.ip, timeout=1) # Fast retries
            if latency is not None:
                break
    
    status = 'ONLINE' if latency is not None else 'TIMEOUT'
    
    # Record history
    HistorialDisponibilidad.objects.create(
        equipo=device,
        latencia_ms=latency if latency else None,
        estado=status,
        packet_loss=100.0 if latency is None else 0.0
    )

    # Update device status
    device.last_seen = timezone.now() if status == 'ONLINE' else device.last_seen
    device.is_online = (status == 'ONLINE')
    device.save()

def poll_devices():
    devices = Equipo.objects.filter(estado='ACTIVO', en_mantenimiento=False)
    for device in devices:
        # Check if we should ping this device? 
        # For simplicity, poll_devices runs every X seconds and pings ALL active devices.
        async_task('monitor.tasks.check_device', device.id)
