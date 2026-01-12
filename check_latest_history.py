import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qawaq_project.settings')
django.setup()

from monitor.models import Equipo, HistorialDisponibilidad

try:
    latest_equipo = Equipo.objects.latest('created_at')
    print(f"Latest Device: {latest_equipo.id_equipo} (ID: {latest_equipo.id})")
    count = HistorialDisponibilidad.objects.filter(equipo=latest_equipo).count()
    print(f"History Count: {count}")
    if count == 0:
        print("This device has no history yet.")
except Equipo.DoesNotExist:
    print("No devices found.")
