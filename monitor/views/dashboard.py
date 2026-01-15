from django.views.generic import TemplateView
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.functions import TruncHour
from django.db.models import DateTimeField

import datetime
import json

from ..decorators import login_required_method
from ..models import Equipo, HistorialDisponibilidad, EventoFacturacion

@login_required_method
class DashboardView(TemplateView):
    template_name = 'monitor/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Top 4 Brands Stats
        # We need: Brand Name, Total Count, Down Count, Status Color (implicit)
        top_brands = Equipo.objects.values('marca__nombre', 'marca__color').annotate(
            total=Count('id'),
            down=Count('id', filter=Q(is_online=False))
        ).order_by('-total')[:4]
        
        context['brand_stats'] = top_brands

        # 2. Network Latency Chart (Last 24h Average)
        # Using local variables instead of importing inside method
        
        # 3. Network Latency Chart (Last 24h Average - Hourly)
        current_tz = timezone.get_current_timezone()
        now = timezone.now()
        start_24h = now - datetime.timedelta(hours=24)
        
        latency_qs = HistorialDisponibilidad.objects.filter(
            timestamp__gte=start_24h,
            estado='ONLINE'
        ).annotate(
            hour=TruncHour('timestamp', output_field=DateTimeField(), tzinfo=current_tz)
        ).values('hour').annotate(
            avg_latency=Avg('latencia_ms')
        ).order_by('hour')
        
        latency_labels = []
        latency_values = []
        for item in latency_qs:
            # Force server-side formatted string labels
            label = item['hour'].strftime('%H:%M')
            val = round(item['avg_latency'], 1)
            latency_labels.append(label)
            latency_values.append(val)
            
        context['latency_labels'] = json.dumps(latency_labels, cls=DjangoJSONEncoder)
        context['latency_data'] = json.dumps(latency_values, cls=DjangoJSONEncoder)
        
        # 3. Packet Loss
        avg_packet_loss = HistorialDisponibilidad.objects.filter(
            timestamp__gte=start_24h
        ).aggregate(avg=Avg('packet_loss'))['avg'] or 0
        context['packet_loss'] = round(avg_packet_loss, 2)

        # 4. Offline Devices List (Enriched with Billing Info)
        # Sort by: 
        # 1. Billing Priority (Has billing event Today or Tomorrow) -> High Priority
        # 2. Downtime Duration (Longest first)
        
        offline_devices = []
        raw_offline = Equipo.objects.filter(is_online=False, estado='ACTIVO').select_related('marca').prefetch_related('medidores_asociados__porcion')
        
        # Pre-fetch future billing events (FACTURACION only)
        # We need to find the NEXT billing date for each portion
        
        today_date = timezone.localdate()
        
        # Get all future billing events sorted by date
        billing_events = EventoFacturacion.objects.filter(
            fecha__gte=today_date,
            tipo_evento='FACTURACION'
        ).order_by('fecha')
        
        # Map porcion_id -> earliest billing date
        porcion_billing_map = {}
        for event in billing_events:
            if event.porcion_id not in porcion_billing_map:
                porcion_billing_map[event.porcion_id] = event.fecha
        
        days_es = {
            0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 
            4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
        }

        for dev in raw_offline:
            # 1. Calculate Downtime
            downtime_str = "N/A"
            downtime_seconds = 0
            
            if dev.last_seen:
                diff = now - dev.last_seen
                downtime_seconds = diff.total_seconds()
                total_seconds = int(downtime_seconds)
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                downtime_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            else:
                downtime_seconds = float('inf') # Treat as longest downtime
            
            # 2. Determine Billing Status
            billing_date = None
            billing_priority = False # True if Today or Tomorrow
            billing_label = "-"
            
            # Check all associated portions for this device
            # A device (colector) might serve multiple portions, take the most critical one (earliest date)
            # Also calculate how many meters are in the portions affecting this date
            
            # First pass: Determine Billing Date
            for medidor in dev.medidores_asociados.all():
                if medidor.porcion_id in porcion_billing_map:
                    p_date = porcion_billing_map[medidor.porcion_id]
                    if billing_date is None or p_date < billing_date:
                        billing_date = p_date
            
            # Second pass: Count meters for that specific date
            afectacion_count = 0
            if billing_date:
                for medidor in dev.medidores_asociados.all():
                    if medidor.porcion_id in porcion_billing_map:
                       if porcion_billing_map[medidor.porcion_id] == billing_date:
                           afectacion_count += 1
            else:
                 # If no billing date, maybe show total meters? Or 0? User said "associated in the portions that are billing on the date indicated". 
                 # So if no date indicated (billing_label="-"), count is 0 not relevant.
                 afectacion_count = 0
            
            if billing_date:
                delta_days = (billing_date - today_date).days
                
                if delta_days == 0:
                    billing_label = "Hoy"
                    billing_priority = True
                elif delta_days == 1:
                    billing_label = "Mañana"
                    billing_priority = True
                elif delta_days < 7:
                    # Show Day Name
                    billing_label = days_es[billing_date.weekday()]
                else:
                    # Show Date
                    billing_label = billing_date.strftime("%d/%m")
            
            # 3. Format "Afectación" label
            afectacion_str = ""
            if billing_date and afectacion_count > 0:
                if afectacion_count == 1:
                    afectacion_str = "1 medidor"
                else:
                    afectacion_str = f"{afectacion_count} medidores"
            
            
            # Only add device if it has billing priority (today or tomorrow) AND has associated medidores
            if billing_priority and afectacion_count > 0:
                offline_devices.append({
                    'id_equipo': dev.id_equipo,
                    'ip': dev.ip,
                    'marca': dev.marca.nombre if dev.marca else 'Desconocido',
                    'downtime': downtime_str,
                    'downtime_seconds': downtime_seconds, # For sorting
                    'billing_priority': billing_priority, # For sorting
                    'billing_label': billing_label,
                    'afectacion_count': afectacion_count,
                    'afectacion_str': afectacion_str,
                    'id': dev.id # for url
                })
            
        # Sort logic: 
        # Primary: billing_priority (True > False) -> Reverse=True handles this? True=1, False=0. Yes.
        # Secondary: downtime_seconds (Biggest > Smallest) -> Reverse=True
        
        offline_devices.sort(key=lambda x: (x['billing_priority'], x['downtime_seconds']), reverse=True)
            
        context['offline_list'] = offline_devices # Show all devices with billing priority (no limit)
        context['total_monitored'] = Equipo.objects.count()
        context['total_down'] = len(raw_offline)
        
        # Billing events for today and tomorrow
        
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        
        # Get FACTURACION events for today
        eventos_hoy = EventoFacturacion.objects.filter(
            fecha=today,
            tipo_evento='FACTURACION'
        ).select_related('porcion').order_by('porcion__nombre')
        
        # Get FACTURACION events for tomorrow
        eventos_manana = EventoFacturacion.objects.filter(
            fecha=tomorrow,
            tipo_evento='FACTURACION'
        ).select_related('porcion').order_by('porcion__nombre')
        
        context['eventos_hoy'] = list(eventos_hoy)
        context['eventos_manana'] = list(eventos_manana)

        return context
