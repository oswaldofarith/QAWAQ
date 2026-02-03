from django.views.generic import ListView, DetailView
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Q
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
import datetime
import json
from django.views.generic import ListView, DetailView, TemplateView

from ..models import Equipo, Marca, TipoEquipo, Porcion, HistorialDisponibilidad
from ..forms import EquipoForm
from ..decorators import login_required_method, admin_required_method

@login_required_method
class EquipoListView(ListView):
    model = Equipo
    template_name = 'monitor/equipo_list.html'
    context_object_name = 'equipos'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['marcas'] = Marca.objects.all()
        context['tipos'] = TipoEquipo.objects.all() # For filter
        context['porciones'] = Porcion.objects.all().order_by('nombre')
        context['total_active'] = Equipo.objects.filter(estado='ACTIVO').count()
        return context

    def get_queryset(self):
        qs = super().get_queryset().select_related('marca', 'tipo').prefetch_related('medidores_asociados__porcion').order_by('id_equipo')
        
        # Filtering
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(ip__icontains=query) | qs.filter(id_equipo__icontains=query)
            
        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
            
        marca_id = self.request.GET.get('marca')
        if marca_id:
            qs = qs.filter(marca_id=marca_id)

        tipo_id = self.request.GET.get('tipo')
        if tipo_id:
            qs = qs.filter(tipo_id=tipo_id)

        medio = self.request.GET.get('medio')
        if medio:
            qs = qs.filter(medio_comunicacion=medio)

        comunicacion = self.request.GET.get('comunicacion')
        if comunicacion:
            if comunicacion == 'ONLINE':
                qs = qs.filter(is_online=True)
            elif comunicacion == 'OFFLINE':
                qs = qs.filter(is_online=False)

        porcion_id = self.request.GET.get('porcion')
        if porcion_id:
            qs = qs.filter(medidores_asociados__porcion_id=porcion_id).distinct()
            
        return qs
        
    def get_template_names(self):
        if self.request.htmx:
            return ['monitor/partials/equipo_list_content.html']
        return ['monitor/equipo_list.html']

class GlobalSearchView(ListView):
    model = Equipo
    template_name = 'monitor/partials/search_results.html'
    context_object_name = 'results'
    paginate_by = 5

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if len(query) < 2:
            return Equipo.objects.none()
        
        return Equipo.objects.filter(
            Q(id_equipo__icontains=query) | 
            Q(ip__icontains=query) |
            Q(marca__nombre__icontains=query)
        ).select_related('marca')[:5]


@login_required_method
class EquipoDetailView(DetailView):
    model = Equipo
    template_name = 'monitor/equipo_detail.html'
    context_object_name = 'equipo'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('medidores_asociados__porcion')


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        now = timezone.now()
        start_time = now - datetime.timedelta(hours=24)
        
        history = HistorialDisponibilidad.objects.filter(
            equipo=self.object,
            timestamp__gte=start_time
        ).values('timestamp', 'latencia_ms', 'estado').order_by('timestamp')
        
        # Prepare data for ApexCharts: Split into labels (server-time) and values
        # Value: 1 for ONLINE, 0 for OFFLINE/TIMEOUT
        chart_labels = []
        chart_values = []
        
        current_tz = timezone.get_current_timezone()
        
        for h in history:
            local_dt = h['timestamp'].astimezone(current_tz)
            chart_labels.append(local_dt.strftime('%d/%m %H:%M'))
            chart_values.append(1 if h['estado'] == 'ONLINE' else 0)
        
        context['chart_labels'] = chart_labels
        context['chart_values'] = chart_values
        
        # Calculate availability for the period (48h)
        total_checks = len(history)
        online_checks = sum(1 for h in history if h['estado'] == 'ONLINE')
        availability = round((online_checks / total_checks * 100), 2) if total_checks > 0 else 0
        context['availability'] = availability
        
        return context

@admin_required_method
class EquipoCreateView(View):
    """Create a new equipment."""
    
    def get(self, request):
        form = EquipoForm()
        return render(request, 'monitor/equipo_form.html', {
            'form': form,
            'title': 'Nuevo Equipo',
            'is_create': True
        })
    
    def post(self, request):
        form = EquipoForm(request.POST)
        if form.is_valid():
            equipo = form.save()
            messages.success(request, f'Equipo "{equipo.id_equipo}" creado exitosamente.')
            return redirect('equipo_detail', pk=equipo.pk)
        return render(request, 'monitor/equipo_form.html', {
            'form': form,
            'title': 'Nuevo Equipo',
            'is_create': True
        })


@admin_required_method
class EquipoUpdateView(View):
    """Update an existing equipment."""
    
    def get(self, request, pk):
        equipo = get_object_or_404(Equipo, pk=pk)
        form = EquipoForm(instance=equipo)
        return render(request, 'monitor/equipo_form.html', {
            'form': form,
            'equipo': equipo,
            'title': 'Editar Equipo',
            'is_create': False
        })
    
    def post(self, request, pk):
        equipo = get_object_or_404(Equipo, pk=pk)
        form = EquipoForm(request.POST, instance=equipo)
        if form.is_valid():
            form.save()
            messages.success(request, f'Equipo "{equipo.id_equipo}" actualizado exitosamente.')
            return redirect('equipo_detail', pk=equipo.pk)
        return render(request, 'monitor/equipo_form.html', {
            'form': form,
            'equipo': equipo,
            'title': 'Editar Equipo',
            'is_create': False
        })


@admin_required_method
class EquipoDeleteView(View):
    """Delete an equipment with confirmation."""
    
    def get(self, request, pk):
        equipo = get_object_or_404(Equipo, pk=pk)
        history_count = equipo.historial.count()
        return render(request, 'monitor/equipo_confirm_delete.html', {
            'equipo': equipo,
            'history_count': history_count
        })
    
    def post(self, request, pk):
        equipo = get_object_or_404(Equipo, pk=pk)
        id_equipo = equipo.id_equipo
        equipo.delete()  # Cascades to historical data
        messages.success(request, f'Equipo "{id_equipo}" eliminado exitosamente.')
        return redirect('equipo_list')


class PingDeviceView(View):
    def post(self, request, pk, *args, **kwargs):
        from ..tasks import ping_host
        
        device = get_object_or_404(Equipo, pk=pk)
        
        # Run synchronous ping (fast timeout for UI)
        latency = ping_host(device.ip, timeout=2)
        
        status = 'ONLINE' if latency is not None else 'OFFLINE'
        
        # Update DB
        if status == 'ONLINE':
            device.last_seen = timezone.now()
            device.is_online = True
            # Update latency history if needed, or just update status
            HistorialDisponibilidad.objects.create(
                equipo=device,
                latencia_ms=latency,
                estado='ONLINE',
                packet_loss=0.0
            )
        else:
            device.is_online = False
            HistorialDisponibilidad.objects.create(
                equipo=device,
                latencia_ms=None,
                estado='OFFLINE',
                packet_loss=100.0
            )
        device.save()
        
        # Trigger client-side event for Toast
        response = HttpResponse(status=200)
        
        payload = {
            "showMessage": {
                "level": "success" if status == 'ONLINE' else "error",
                "message": f"Ping a {device.ip}: {status} ({latency}ms)" if latency else f"Ping a {device.ip}: {status}"
            }
        }
        response['HX-Trigger'] = json.dumps(payload)
        return response

class PingModalView(View):
    def get(self, request, pk, *args, **kwargs):
        device = get_object_or_404(Equipo, pk=pk)
        return render(request, 'monitor/partials/ping_modal.html', {'equipo': device})

class PingToolView(View):
    def get(self, request, pk, *args, **kwargs):
        from ..tasks import ping_host
        
        device = get_object_or_404(Equipo, pk=pk)
        latency = ping_host(device.ip, timeout=0.8) # Fast timeout for real-time feel
        
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        
        if latency is not None:
             html = f'<div class="mb-1"><span class="text-white-50">[{timestamp}]</span> Respuesta desde <b class="text-white">{device.ip}</b>: tiempo={latency}ms TTL=64</div>'
        else:
             html = f'<div class="mb-1"><span class="text-white-50">[{timestamp}]</span> <span class="text-danger">Tiempo de espera agotado para esta solicitud.</span></div>'
             
             
        return HttpResponse(html)


class TracerouteModalView(View):
    def get(self, request, pk, *args, **kwargs):
        device = get_object_or_404(Equipo, pk=pk)
        return render(request, 'monitor/partials/traceroute_modal.html', {'equipo': device})


class TracerouteToolView(View):
    def get(self, request, pk, *args, **kwargs):
        import subprocess
        import platform
        
        device = get_object_or_404(Equipo, pk=pk)
        
        # Determine traceroute command based on OS
        if platform.system() == 'Windows':
            cmd = ['tracert', '-d', '-w', '1000', '-h', '15', device.ip]
        else:
            cmd = ['traceroute', '-n', '-w', '1', '-m', '15', device.ip]
        
        try:
            # Execute traceroute command
            # Don't specify encoding - let Python use system default (CP850/CP1252 on Windows)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout if result.stdout else result.stderr
            
            # Format output for HTML display
            html_lines = []
            for line in output.split('\n'):
                if line.strip():
                    # Highlight IP addresses and hop numbers
                    formatted_line = line.replace('<', '&lt;').replace('>', '&gt;')
                    html_lines.append(f'<div class="mb-1 text-info">{formatted_line}</div>')
            
            html = ''.join(html_lines) if html_lines else '<div class="text-warning">No se recibió salida del comando traceroute.</div>'
            
        except subprocess.TimeoutExpired:
            html = '<div class="text-danger">Tiempo de espera agotado para traceroute.</div>'
        except Exception as e:
            html = f'<div class="text-danger">Error al ejecutar traceroute: {str(e)}</div>'
        
        return HttpResponse(html)

class MapaView(TemplateView):
    """Vista de mapa interactivo con equipos y su estado."""
    template_name = 'monitor/mapa.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        marca_filter = self.request.GET.get('marca', '')
        medio_filter = self.request.GET.get('medio', '')
        estado_filter = self.request.GET.get('estado', '')
        porcion_filter = self.request.GET.get('porcion', '')
        
        # Guayaquil bounds
        GUAYAQUIL_BOUNDS = {
            'min_lat': -2.35,
            'max_lat': -1.95,
            'min_lng': -80.15,
            'max_lng': -79.65
        }
        
        # Filter equipos with valid coordinates within Guayaquil
        equipos = Equipo.objects.filter(
            latitud__isnull=False,
            longitud__isnull=False,
            latitud__gte=GUAYAQUIL_BOUNDS['min_lat'],
            latitud__lte=GUAYAQUIL_BOUNDS['max_lat'],
            longitud__gte=GUAYAQUIL_BOUNDS['min_lng'],
            longitud__lte=GUAYAQUIL_BOUNDS['max_lng']
        ).select_related('marca', 'tipo')
        
        # Apply filters
        if marca_filter:
            equipos = equipos.filter(marca_id=marca_filter)
        
        if medio_filter:
            equipos = equipos.filter(medio_comunicacion=medio_filter)
        
        if estado_filter:
            if estado_filter == 'ONLINE':
                equipos = equipos.filter(is_online=True, estado='ACTIVO')
            elif estado_filter == 'OFFLINE':
                equipos = equipos.filter(is_online=False, estado='ACTIVO')
            elif estado_filter == 'MANTENIMIENTO':
                equipos = equipos.filter(estado='EN_MANTENIMIENTO')

        if porcion_filter:
            equipos = equipos.filter(medidores_asociados__porcion_id=porcion_filter).distinct()
        
        # Serialize equipos to JSON
        equipos_data = []
        for equipo in equipos:
            # Determine marker color logic: Maintenance (Yellow) > Offline (Red) > Online (Green)
            if equipo.estado == 'EN_MANTENIMIENTO':
                color = '#ffc107' # Bright yellow
                estado_text = 'Mantenimiento'
            elif not equipo.is_online:
                color = 'red'
                estado_text = 'Offline'
            else:
                color = 'green'
                estado_text = 'Online'
            
            equipos_data.append({
                'id': equipo.id,
                'id_equipo': equipo.id_equipo,
                'ip': equipo.ip,
                'lat': float(equipo.latitud),
                'lng': float(equipo.longitud),
                'color': color,
                'estado': estado_text,
                'marca': equipo.marca.nombre if equipo.marca else 'N/A',
                'tipo': equipo.tipo.nombre if equipo.tipo else 'N/A',
                'comunicacion': equipo.get_medio_comunicacion_display(),
                'direccion': equipo.direccion or 'N/A',
                'poste': equipo.poste or 'N/A',
            })
        
        context['equipos_json'] = json.dumps(equipos_data)
        context['marcas'] = Marca.objects.all()
        context['marca_filter'] = marca_filter
        context['medio_filter'] = medio_filter
        context['estado_filter'] = estado_filter
        context['porcion_filter'] = porcion_filter
        context['porciones'] = Porcion.objects.all().order_by('nombre')
        context['total_equipos'] = len(equipos_data)
        
        return context

@admin_required_method
class ToggleMaintenanceView(View):
    """Toggle maintenance status for an equipment."""
    
    def post(self, request, pk):
        equipo = get_object_or_404(Equipo, pk=pk)
        
        # Toggle boolean
        equipo.en_mantenimiento = not equipo.en_mantenimiento
        
        # Sync with estado field if appropriate
        if equipo.en_mantenimiento:
            if equipo.estado == 'ACTIVO':
                equipo.estado = 'EN_MANTENIMIENTO'
        else:
            if equipo.estado == 'EN_MANTENIMIENTO':
                equipo.estado = 'ACTIVO'
        
        equipo.save()
        
        # If HTMX, return just the row
        if request.htmx:
            return render(request, 'monitor/partials/equipo_list_rows.html', {'equipos': [equipo]})
        
        messages.success(request, f'Estado de mantenimiento de "{equipo.id_equipo}" actualizado.')
        return redirect('equipo_list')
