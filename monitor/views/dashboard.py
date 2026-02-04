from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
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
            down=Count('id', filter=Q(is_online=False, estado='ACTIVO')),
            maintenance=Count('id', filter=Q(estado='EN_MANTENIMIENTO'))
        ).order_by('-total')[:4]
        
        context['brand_stats'] = top_brands

        # 2. Network Latency Chart (Last 24h Average)
        # Using local variables instead of importing inside method
        
        # 3. Network Latency Chart (Last 24h Average - Hourly)
        current_tz = timezone.get_current_timezone()
        now = timezone.now()
        start_24h = now - datetime.timedelta(hours=24)
        
        # Base QuerySet for hourly grouping
        base_qs = HistorialDisponibilidad.objects.filter(
            timestamp__gte=start_24h,
            estado='ONLINE'
        ).annotate(
            hour=TruncHour('timestamp', output_field=DateTimeField(), tzinfo=current_tz)
        )

        # 1. FIBRA Average
        latency_fibra = base_qs.filter(
            equipo__medio_comunicacion='FIBRA'
        ).values('hour').annotate(
            avg_latency=Avg('latencia_ms')
        ).order_by('hour')
        
        # 2. CELULAR Average
        latency_celular = base_qs.filter(
            equipo__medio_comunicacion='CELULAR'
        ).values('hour').annotate(
            avg_latency=Avg('latencia_ms')
        ).order_by('hour')
        
        # Helper to create time series dict
        def create_time_series(queryset):
            data = {}
            for item in queryset:
                label = item['hour'].strftime('%H:%M')
                val = round(item['avg_latency'], 1)
                data[label] = val
            return data

        fibra_map = create_time_series(latency_fibra)
        celular_map = create_time_series(latency_celular)
        
        # Generate unified labels (all hours found in either set)
        all_labels = sorted(list(set(list(fibra_map.keys()) + list(celular_map.keys()))))
        
        # Align data to labels (fill missing with None or previous value? ApexCharts handles None as gap)
        # For better visual, we'll align values. If a timestamp is missing for one series, we send null
        
        fibra_values = [fibra_map.get(label, None) for label in all_labels]
        celular_values = [celular_map.get(label, None) for label in all_labels]
            
        context['latency_labels'] = json.dumps(all_labels, cls=DjangoJSONEncoder)
        context['latency_data_fibra'] = json.dumps(fibra_values, cls=DjangoJSONEncoder)
        context['latency_data_celular'] = json.dumps(celular_values, cls=DjangoJSONEncoder)
        
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
            
            # 2. Find Nearest Billing Date
            billing_date = None
            
            # Find earliest billing date among all portions associated with this device
            for medidor in dev.medidores_asociados.all():
                if medidor.porcion_id in porcion_billing_map:
                    p_date = porcion_billing_map[medidor.porcion_id]
                    if billing_date is None or p_date < billing_date:
                        billing_date = p_date
            
            # 3. Add to list if applicable
            if billing_date:
                # Count meters affected by THIS specific billing date
                afectacion_count = 0
                for medidor in dev.medidores_asociados.all():
                    if medidor.porcion_id in porcion_billing_map and porcion_billing_map[medidor.porcion_id] == billing_date:
                        afectacion_count += 1
                
                if afectacion_count > 0:
                    delta_days = (billing_date - today_date).days
                    billing_label = ""
                    
                    if delta_days == 0:
                        billing_label = "Hoy"
                    elif delta_days == 1:
                        billing_label = "Mañana"
                    else:
                        billing_label = billing_date.strftime("%d/%m")
                    
                    afectacion_str = "1 medidor" if afectacion_count == 1 else f"{afectacion_count} medidores"
                    
                    offline_devices.append({
                        'id_equipo': dev.id_equipo,
                        'ip': dev.ip,
                        'marca': dev.marca.nombre if dev.marca else 'Desconocido',
                        'downtime': downtime_str,
                        'downtime_seconds': downtime_seconds,
                        'delta_days': delta_days,
                        'billing_label': billing_label,
                        'billing_priority': delta_days <= 1, # Preserve for template styling
                        'afectacion_count': afectacion_count,
                        'afectacion_str': afectacion_str,
                        'id': dev.id
                    })
            
        # Sort: Nearest billing first (small delta), then longest downtime (big seconds -> negative for descending)
        offline_devices.sort(key=lambda x: (x['delta_days'], -x['downtime_seconds']))
        
        # Limit to top 8 priority devices
        offline_devices = offline_devices[:8]
            
        context['offline_list'] = offline_devices
        context['total_monitored'] = Equipo.objects.count()
        context['total_down'] = Equipo.objects.filter(is_online=False, estado='ACTIVO').count()
        context['total_online'] = Equipo.objects.filter(is_online=True, estado='ACTIVO').count()
        context['total_maintenance'] = Equipo.objects.filter(estado='EN_MANTENIMIENTO').count()
        
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

class NOCView(LoginRequiredMixin, TemplateView):
    template_name = 'monitor/noc_view.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        today = now.date()
        tomorrow = today + datetime.timedelta(days=1)
        start_24h = now - datetime.timedelta(hours=24)
        
        # 1. Global Stats
        context['total_equipos'] = Equipo.objects.count()
        context['online_count'] = Equipo.objects.filter(is_online=True, estado='ACTIVO').count()
        context['offline_count'] = Equipo.objects.filter(is_online=False, estado='ACTIVO').count()
        context['maintenance_count'] = Equipo.objects.filter(estado='EN_MANTENIMIENTO').count()
        
        # 2. Daily Failure Count (total checks that resulted in OFFLINE in last 24h)
        # This remains unchanged as it counts historical check events
        context['failures_24h'] = HistorialDisponibilidad.objects.filter(
            timestamp__gte=start_24h,
            estado='OFFLINE'
        ).count()

        # 3. Critical Failures: Equipment with meters in portions being billed today or tomorrow
        
        # Get portions with billing events today or tomorrow
        critical_portions = EventoFacturacion.objects.filter(
            fecha__in=[today, tomorrow]
        ).values_list('porcion_id', flat=True).distinct()
        
        # Get equipment that:
        # - Is currently offline
        # - Has meters associated with critical portions
        critical_failures = Equipo.objects.filter(
            is_online=False,
            estado='ACTIVO',
            medidores_asociados__porcion_id__in=critical_portions
        ).distinct().select_related('marca', 'tipo').prefetch_related('medidores_asociados__porcion')
        
        # Enriched critical failure list for NOC
        failure_list = []
        for dev in critical_failures:
            downtime_str = "N/A"
            downtime_seconds = 0
            if dev.last_seen:
                diff = now - dev.last_seen
                total_seconds = int(diff.total_seconds())
                downtime_seconds = total_seconds
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                downtime_str = f"{hours:02}:{minutes:02}"
            
            # Get billing events for this equipment's portions
            billing_events = EventoFacturacion.objects.filter(
                porcion__in=dev.medidores_asociados.values_list('porcion', flat=True),
                fecha__in=[today, tomorrow]
            ).select_related('porcion')
            
            # Check if has billing today (not tomorrow)
            has_billing_today = billing_events.filter(fecha=today).exists()
            
            failure_list.append({
                'id_equipo': dev.id_equipo,
                'ip': dev.ip,
                'marca': dev.marca.nombre if dev.marca else 'N/A',
                'tipo': dev.tipo.nombre if dev.tipo else 'N/A',
                'medio': dev.medio_comunicacion if dev.medio_comunicacion else 'N/A',
                'downtime': downtime_str,
                'downtime_seconds': downtime_seconds,
                'has_billing_today': has_billing_today,
                'porcion_nombres': [evt.porcion.nombre for evt in billing_events[:3]],
                'billing_dates': [evt.fecha.strftime('%d/%m') for evt in billing_events[:3]]
            })

        # Sort: 1) Billing today first, 2) Then by shortest downtime (most recent failures)
        failure_list.sort(key=lambda x: (not x['has_billing_today'], x['downtime_seconds']))
        context['critical_failures'] = failure_list

        # 4. Map Data - All equipment with coordinates (Active or Maintenance)
        equipos = Equipo.objects.filter(
            Q(estado='ACTIVO') | Q(estado='EN_MANTENIMIENTO')
        ).select_related('marca', 'tipo').prefetch_related('medidores_asociados__porcion')
        
        equipos_data = []
        for eq in equipos:
            if eq.latitud and eq.longitud:
                # Color logic: Maintenance (Yellow) > Offline (Red) > Online (Green)
                if eq.estado == 'EN_MANTENIMIENTO':
                    marker_color = '#ffc107' # Bright Yellow
                elif not eq.is_online:
                    marker_color = '#da3633' # --noc-offline
                else:
                    marker_color = '#238636' # --noc-online

                equipos_data.append({
                    'id_equipo': eq.id_equipo,
                    'ip': eq.ip,
                    'lat': float(eq.latitud),
                    'lng': float(eq.longitud),
                    'is_online': eq.is_online,
                    'marker_color': marker_color,
                    'estado': eq.get_estado_display(),
                    'marca': eq.marca.nombre if eq.marca else 'N/A',
                    'tipo': eq.tipo.nombre if eq.tipo else 'N/A',
                    'last_seen': eq.last_seen.strftime('%Y-%m-%d %H:%M') if eq.last_seen else 'N/A',
                })
        
        context['equipos_json'] = json.dumps(equipos_data, cls=DjangoJSONEncoder)

        return context

