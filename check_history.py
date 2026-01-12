import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qawaq_project.settings')
django.setup()

from monitor.models import Equipo, HistorialDisponibilidad

print(f"Total History Records: {HistorialDisponibilidad.objects.count()}")

equipos = Equipo.objects.all()
for e in equipos:
    count = HistorialDisponibilidad.objects.filter(equipo=e).count()
    print(f"Device {e.id_equipo} (ID: {e.id}): {count} history records")
    if count > 0:
        latest = HistorialDisponibilidad.objects.filter(equipo=e).latest('timestamp')
        print(f"  Latest: {latest.timestamp} - {latest.latencia_ms}ms")
