from django.views.generic import ListView, TemplateView
from django.db.models import Count, Q, Avg
from django.utils import timezone
import datetime
from ..models import Equipo, HistorialDisponibilidad, Marca

class ReporteView(ListView):
    model = Equipo
    template_name = 'monitor/reportes.html'
    context_object_name = 'equipos'
    paginate_by = 10

    def get_queryset(self):
        now = timezone.now()
        
        # Date Range Filtering
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            try:
                # Use current active timezone (America/Lima) to parse expected range
                current_tz = timezone.get_current_timezone()
                
                # Start of day
                naive_start = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
                start_date = timezone.make_aware(naive_start, current_tz)
                
                # End of day
                naive_end = datetime.datetime.strptime(end_date_str, '%Y-%m-%d') + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)
                end_date = timezone.make_aware(naive_end, current_tz)
            except ValueError:
                start_date = now - datetime.timedelta(days=30)
                end_date = now
        else:
            start_date = now - datetime.timedelta(days=30)
            end_date = now

        # Calculate availability based on Ping History in Range
        qs = Equipo.objects.filter(estado='ACTIVO').annotate(
            total_checks=Count('historial', filter=Q(historial__timestamp__gte=start_date, historial__timestamp__lte=end_date)),
            online_checks=Count('historial', filter=Q(historial__timestamp__gte=start_date, historial__timestamp__lte=end_date, historial__estado='ONLINE'))
        )
        
        # Filtering
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(Q(ip__icontains=query) | Q(id_equipo__icontains=query))
            
        marca_id = self.request.GET.get('marca')
        if marca_id:
            qs = qs.filter(marca_id=marca_id)

        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
            
        qs = qs.order_by('id_equipo')
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Current filter values
        try:
            current_marca_id = int(self.request.GET.get('marca', 0))
        except (ValueError, TypeError):
            current_marca_id = 0
            
        current_estado = self.request.GET.get('estado', '')

        # Prepare Marcas with selected flag
        marcas_list = []
        all_marcas = Marca.objects.all()
        for m in all_marcas:
            marcas_list.append({
                'id': m.id,
                'nombre': m.nombre,
                'selected': m.id == current_marca_id
            })
        context['marcas_list'] = marcas_list

        # Prepare Estados with selected flag
        estados_list = [
            {'value': '', 'label': 'Todos', 'selected': current_estado == ''},
            {'value': 'ACTIVO', 'label': 'Activo', 'selected': current_estado == 'ACTIVO'},
            {'value': 'INACTIVO', 'label': 'Inactivo', 'selected': current_estado == 'INACTIVO'},
        ]
        context['estados_list'] = estados_list
        
        # Pass back dates for form
        start_date_str = self.request.GET.get('start_date', '')
        end_date_str = self.request.GET.get('end_date', '')
        context['start_date'] = start_date_str
        context['end_date'] = end_date_str

        # Pre-calculate percentage for template
        for equipo in context['equipos']:
            if equipo.total_checks > 0:
                equipo.availability = round((equipo.online_checks / equipo.total_checks) * 100, 1)
                equipo.downtime_count = equipo.total_checks - equipo.online_checks
            else:
                equipo.availability = 0
                equipo.downtime_count = 0

        # --- MERGED DASHBOARD STATS (from duplicate method) ---
        
        # Recalculate range for global stats if needed, or use default last 24h
        now = timezone.now()
        last_24h = now - datetime.timedelta(hours=24)
        last_7d = now - datetime.timedelta(days=7)

        # 1. Total Outages (Last 24h)
        total_outages_24h = HistorialDisponibilidad.objects.filter(
            timestamp__gte=last_24h,
            estado='OFFLINE'
        ).count()
        context['total_outages_24h'] = total_outages_24h

        # 2. Global Average Latency (Last 24h)
        avg_latency_24h = HistorialDisponibilidad.objects.filter(
            timestamp__gte=last_24h,
            latencia_ms__isnull=False
        ).aggregate(Avg('latencia_ms'))['latencia_ms__avg']
        context['avg_latency_24h'] = round(avg_latency_24h or 0, 1)

        # 3. Worst Performing Devices (Most Offline events in last 7d)
        worst_devices = Equipo.objects.filter(
            historial__timestamp__gte=last_7d,
            historial__estado='OFFLINE'
        ).annotate(
            offline_count=Count('historial')
        ).order_by('-offline_count')[:5]
        context['worst_devices'] = worst_devices

        return context

class ReporteIndividualView(TemplateView):
    template_name = 'monitor/reporte_individual.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Handle Device Selection by String ID (id_equipo)
        equipo_code = self.request.GET.get('equipo_code')
        
        # List for search dropdown (include brand)
        context['equipos_search'] = Equipo.objects.filter(estado='ACTIVO').values('id', 'id_equipo', 'ip', 'marca__nombre').order_by('id_equipo')
        
        if equipo_code:
            # Try to find by id_equipo, or fall back to PK if it's numeric (legacy support)
            equipo = None
            try:
                equipo = Equipo.objects.get(id_equipo=equipo_code)
            except Equipo.DoesNotExist:
                # Fallback: maybe passed PK?
                if str(equipo_code).isdigit():
                    try:
                        equipo = Equipo.objects.get(pk=equipo_code)
                    except Equipo.DoesNotExist:
                        pass
            
            
            if equipo:
                context['selected_equipo'] = equipo
            
            # 2. Parse Dates (Reuse logic or keep simple default 30d)
            start_date_str = self.request.GET.get('start_date')
            end_date_str = self.request.GET.get('end_date')
            now = timezone.now()
            
            if start_date_str and end_date_str:
                try:
                    current_tz = timezone.get_current_timezone()
                    naive_start = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
                    start_date = timezone.make_aware(naive_start, current_tz)
                    naive_end = datetime.datetime.strptime(end_date_str, '%Y-%m-%d') + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)
                    end_date = timezone.make_aware(naive_end, current_tz)
                except ValueError:
                    start_date = now - datetime.timedelta(days=30)
                    end_date = now
            else:
                start_date = now - datetime.timedelta(days=30)
                end_date = now
            
            context['start_date'] = start_date_str or start_date.date().isoformat()
            context['end_date'] = end_date_str or end_date.date().isoformat()

            # 3. Calculate Availability
            total = HistorialDisponibilidad.objects.filter(
                equipo=equipo,
                timestamp__range=(start_date, end_date)
            ).count()
            
            online = HistorialDisponibilidad.objects.filter(
                equipo=equipo,
                timestamp__range=(start_date, end_date),
                estado='ONLINE'
            ).count()
            
            availability = round((online / total * 100), 2) if total > 0 else 0
            context['availability'] = availability
            context['total_checks'] = total
            context['downtime_count'] = total - online

            # 4. Downtime Incidents - Group consecutive OFFLINE events
            all_history = HistorialDisponibilidad.objects.filter(
                equipo=equipo,
                timestamp__range=(start_date, end_date)
            ).order_by('timestamp').values('timestamp', 'estado')
            
            # Group consecutive OFFLINE periods into incidents
            incidents = []
            current_incident = None
            
            for record in all_history:
                if record['estado'] == 'OFFLINE':
                    if current_incident is None:
                        # Start new incident
                        current_incident = {
                            'start': record['timestamp'],
                            'end': record['timestamp']
                        }
                    else:
                        # Extend current incident
                        current_incident['end'] = record['timestamp']
                else:  # ONLINE
                    if current_incident is not None:
                        # Close incident and calculate duration
                        duration = current_incident['end'] - current_incident['start']
                        incidents.append({
                            'start': current_incident['start'],
                            'end': current_incident['end'],
                            'duration': duration,
                            'duration_str': str(duration).split('.')[0]  # Remove microseconds
                        })
                        current_incident = None
            
            # Close any remaining incident
            if current_incident is not None:
                duration = current_incident['end'] - current_incident['start']
                incidents.append({
                    'start': current_incident['start'],
                    'end': current_incident['end'],
                    'duration': duration,
                    'duration_str': str(duration).split('.')[0]
                })
            
            context['downtime_logs'] = incidents

            # 5. Chart Data
            chart_history = HistorialDisponibilidad.objects.filter(
                equipo=equipo,
                timestamp__range=(start_date, end_date)
            ).order_by('timestamp').values('timestamp', 'estado')
            
            chart_labels = []
            chart_values = []
            
            current_tz = timezone.get_current_timezone()
            
            for h in chart_history:
                local_dt = h['timestamp'].astimezone(current_tz)
                chart_labels.append(local_dt.strftime('%d/%m %H:%M'))
                chart_values.append(1 if h['estado'] == 'ONLINE' else 0)
            
            context['chart_labels'] = chart_labels
            context['chart_values'] = chart_values
            
        return context
