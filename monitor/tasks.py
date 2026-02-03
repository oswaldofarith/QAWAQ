from django_q.tasks import async_task
from django.utils import timezone
from .models import Equipo, HistorialDisponibilidad, ConfiguracionGlobal, Servidor
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


from pysnmp.hlapi import *

def check_server_ping(server_id):
    """Verifica disponibilidad del servidor mediante ICMP (Ping)."""
    try:
        server = Servidor.objects.get(id=server_id)
        config = ConfiguracionGlobal.load()
        
        # Ping
        latency = ping_host(server.ip_address, timeout=2) # 2s default
        
        # Reintentos de Ping
        if latency is None and config.reintentos > 0:
            for _ in range(config.reintentos):
                latency = ping_host(server.ip_address, timeout=1)
                if latency is not None:
                    break
        
        # Actualizar estado
        status = 'ONLINE' if latency is not None else 'OFFLINE'
        server.estado = status
        
        if status == 'ONLINE':
            server.last_seen = timezone.now()
            
        server.save()
        
        # Si está online, disparar recolección de métricas
        if status == 'ONLINE' and config.snmp_user:
            async_task('monitor.tasks.collect_server_metrics', server_id)
            
    except Exception as e:
        logger.error(f"Error en check_server_ping para {server_id}: {e}")


def collect_server_metrics(server_id):
    """Recolecta métricas (CPU, RAM, Disco) via SNMP v3 si el servidor está ONLINE."""
    try:
        server = Servidor.objects.get(id=server_id)
        config = ConfiguracionGlobal.load()
        
        if not config.snmp_user:
            return

        # Config SNMP User
        auth_protocols = {
            'MD5': usmHMACMD5AuthProtocol,
            'SHA': usmHMACSHAAuthProtocol,
            'NONE': usmNoAuthProtocol,
        }
        priv_protocols = {
            'DES': usmDESPrivProtocol,
            'AES': usmAesCfb128Protocol,
            'NONE': usmNoPrivProtocol,
        }
        
        user_data = UsmUserData(
            config.snmp_user,
            config.snmp_auth_key or None,
            config.snmp_priv_key or None,
            authProtocol=auth_protocols.get(config.snmp_auth_protocol, usmHMACSHAAuthProtocol),
            privProtocol=priv_protocols.get(config.snmp_priv_protocol, usmAesCfb128Protocol),
        )
        engine = SnmpEngine()
        target = UdpTransportTarget((server.ip_address, 161), timeout=2.0, retries=1)
        context = ContextData()

        # OIDs Comunes (Linux/Windows con SNMP standard)
        # Load Average (1 min): .1.3.6.1.4.1.2021.10.1.3.1 (UCD-SNMP-MIB)
        # Mem Total: .1.3.6.1.4.1.2021.4.5.0 (kB)
        # Mem Avail: .1.3.6.1.4.1.2021.4.6.0 (kB)
        # SysUpTime: .1.3.6.1.2.1.1.3.0
        
        oids = {
            'sysUpTime': ObjectType(ObjectIdentity('1.3.6.1.2.1.1.3.0')),
            'memTotal': ObjectType(ObjectIdentity('1.3.6.1.4.1.2021.4.5.0')), # kB
            'memAvail': ObjectType(ObjectIdentity('1.3.6.1.4.1.2021.4.6.0')), # kB
            'load1': ObjectType(ObjectIdentity('1.3.6.1.4.1.2021.10.1.3.1')), 
        }
        
        iterator = getCmd(
            engine, user_data, target, context,
            oids['sysUpTime'], oids['memTotal'], oids['memAvail'], oids['load1']
        )
        
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        
        if errorIndication or errorStatus:
            logger.warning(f"SNMP Metrics Error {server.nombre}: {errorIndication or errorStatus}")
            return

        # Parsear resultados
        # varBinds orden: sysUpTime, memTotal, memAvail, load1
        
        # UpTime
        if len(varBinds) >= 1:
            server.uptime = str(varBinds[0][1])
            
        # Memory (Convertir kB a Bytes)
        if len(varBinds) >= 3:
            try:
                total_kb = int(varBinds[1][1])
                avail_kb = int(varBinds[2][1])
                server.memory_total = total_kb * 1024
                # Used = Total - Avail
                server.memory_used = (total_kb - avail_kb) * 1024
            except:
                pass

        # CPU Load
        if len(varBinds) >= 4:
            try:
                # load1 suele ser float
                server.cpu_usage = float(varBinds[3][1])
            except:
                pass
                
        server.save()

    except Exception as e:
        logger.error(f"Error collecting metrics for {server_id}: {e}")

# Legacy Support / Alias
def check_server_snmp(server_id):
    """
    Deprecated: Forwarder function for old queued tasks.
    Redirects to the new availability check.
    """
    return check_server_ping(server_id)

def check_equipment_alerts_task():
    """Wrapper to run the check_equipment_alerts management command from Django Q."""
    from django.core.management import call_command
    call_command('check_equipment_alerts')

def poll_servers():
    """Tarea programada para revisar todos los servidores."""
    servers = Servidor.objects.all()
    for server in servers:
        # Primero Ping (rápido y barato)
        async_task('monitor.tasks.check_server_ping', server.id)


