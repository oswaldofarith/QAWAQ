import os
import django
import json
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qawaq_project.settings')
django.setup()

from monitor.models import Equipo, HistorialDisponibilidad

# Get a device that has history
equipo = Equipo.objects.filter(historial__isnull=False).distinct().first()

if not equipo:
    print("No devices with history found.")
else:
    print(f"Testing for device: {equipo.id_equipo}")
    
    now = timezone.now()
    start_time = now - datetime.timedelta(hours=48)
    
    history = HistorialDisponibilidad.objects.filter(
        equipo=equipo,
        timestamp__gte=start_time
    ).values('timestamp', 'latencia_ms').order_by('timestamp')
    
    print(f"Found {history.count()} records max 48h old.")
    
    chart_data = []
    for h in history:
        val = h['latencia_ms'] if h['latencia_ms'] is not None else 0
        chart_data.append([h['timestamp'].timestamp()*1000, val])
    
    json_output = json.dumps(chart_data, cls=DjangoJSONEncoder)
    print("JSON Output length:", len(json_output))
    print("Sample:", json_output[:100], "...", json_output[-100:])
