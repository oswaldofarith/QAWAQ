import calendar
from datetime import date
from django.views.generic import ListView, TemplateView
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Q, Subquery, OuterRef
from django.utils import timezone
import datetime

from ..models import Porcion, EventoFacturacion, Medidor, Equipo, HistorialDisponibilidad
# from ..models import CicloFacturacion # It was imported in source but maybe not used or used in future? Keep it if needed.
from ..forms import PorcionForm, EventoFacturacionForm
from ..decorators import login_required_method, admin_required_method, admin_required
from django.contrib.auth.decorators import login_required

@login_required_method
class CalendarioView(TemplateView):
    """View to display the monthly billing calendar."""
    template_name = 'monitor/calendario.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = date.today()
        # We pass initial date if provided in URL, for JS to init calendar
        anio = self.kwargs.get('anio')
        mes = self.kwargs.get('mes')
        if anio and mes:
            context['initial_date'] = f"{anio}-{mes:02d}-01"
        else:
            context['initial_date'] = date.today().strftime('%Y-%m-%d')
            
        # Determine Edit Mode
        # Only admins can edit, and only if ?mode=edit is present
        is_admin = False
        if hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin':
            is_admin = True
            
        edit_mode = False
        if is_admin and self.request.GET.get('mode') == 'edit':
             edit_mode = True
             
        context['is_admin'] = is_admin
        context['edit_mode'] = edit_mode
            
        return context


# ==================== API ENDPOINTS FOR CALENDAR ====================

import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

@login_required
@require_GET
def api_get_events(request):
    """Return events for FullCalendar."""
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    
    # FullCalendar sends ISO8601 strings
    start = start_str[:10] if start_str else None
    end = end_str[:10] if end_str else None
    
    query = EventoFacturacion.objects.filter(tipo_evento='FACTURACION')
    if start:
        query = query.filter(fecha__gte=start)
    if end:
        query = query.filter(fecha__lte=end)
        
    events = []
    for event in query.select_related('porcion', 'ciclo').annotate(medidores_count=Count('porcion__medidores')):
        events.append({
            'id': event.id,
            'title': f"{event.porcion.nombre} ({event.medidores_count})",
            'start': event.fecha.isoformat(),
            'backgroundColor': event.get_color(),
            'borderColor': event.get_color(),
            'extendedProps': {
                'porcion_id': event.porcion.id,
                'tipo': event.tipo_evento,
                'medidores_count': event.medidores_count
            }
        })
    
    return JsonResponse(events, safe=False)

@login_required
@require_GET
def api_get_pending_portions(request):
    """Return portions that do NOT have an event in the specified month."""
    import datetime
    
    ref_date_str = request.GET.get('date')
    if ref_date_str:
        try:
            ref_date = datetime.datetime.strptime(ref_date_str[:10], '%Y-%m-%d').date()
        except ValueError:
            ref_date = date.today()
    else:
        ref_date = date.today()
        
    year = ref_date.year
    month = ref_date.month
    
    # Get IDs of portions that HAVE an event in this month
    portions_with_events = EventoFacturacion.objects.filter(
        fecha__year=year,
        fecha__month=month,
        tipo_evento='FACTURACION'
    ).values_list('porcion_id', flat=True)
    
    # Get all portions excluding those
    pending = Porcion.objects.filter(
        # We might want to filter by active status if that existed, but for now all portions
    ).exclude(id__in=portions_with_events).annotate(
        medidores_count=Count('medidores')
    ).values('id', 'nombre', 'tipo', 'medidores_count').order_by('nombre')
    
    data = []
    for p in pending:
        data.append({
            'id': p['id'],
            'title': p['nombre'],
            'medidores_count': p['medidores_count'],
            'tipo': p['tipo'],
            'color': '#EF5350' if p['tipo'] == 'MASIVO' else '#87CEEB'
        })
        
    return JsonResponse(data, safe=False)

@admin_required
@require_POST
def api_save_event(request):
    """Create a new event (when dropped from sidebar)."""
    try:
        data = json.loads(request.body)
        porcion_id = data.get('porcion_id')
        date_str = data.get('date')
        
        if not porcion_id or not date_str:
            return JsonResponse({'error': 'Missing parameters'}, status=400)
            
        fecha = datetime.datetime.strptime(date_str[:10], '%Y-%m-%d').date()
        
        porcion = Porcion.objects.get(pk=porcion_id)
        
        # Check if Cycle exists matches month/year and type
        ciclo, created = CicloFacturacion.objects.get_or_create(
            mes=fecha.month,
            anio=fecha.year,
            tipo=porcion.tipo
        )
        
        if EventoFacturacion.objects.filter(ciclo=ciclo, porcion=porcion, tipo_evento='FACTURACION').exists():
             return JsonResponse({'error': 'Evento ya existe para este ciclo'}, status=400)

        evento = EventoFacturacion.objects.create(
            ciclo=ciclo,
            porcion=porcion,
            fecha=fecha,
            tipo_evento='FACTURACION'
        )
        
        return JsonResponse({
            'id': evento.id,
            'message': 'Evento creado'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@admin_required
@require_POST
def api_update_event(request):
    """Update event date (when moved in calendar)."""
    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        new_date_str = data.get('date')
        
        if not event_id or not new_date_str:
            return JsonResponse({'error': 'Missing parameters'}, status=400)
            
        evento = EventoFacturacion.objects.get(pk=event_id)
        new_date = datetime.datetime.strptime(new_date_str[:10], '%Y-%m-%d').date()
        
        # Check for month/year change to update cycle
        if evento.fecha.month != new_date.month or evento.fecha.year != new_date.year:
            ciclo, created = CicloFacturacion.objects.get_or_create(
                mes=new_date.month,
                anio=new_date.year,
                tipo=evento.porcion.tipo
            )
            evento.ciclo = ciclo
            
        evento.fecha = new_date
        evento.save()
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@admin_required
@require_POST
def api_delete_event(request):
    """Delete event."""
    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        
        evento = EventoFacturacion.objects.get(pk=event_id)
        evento.delete()
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required_method
class EventoListView(ListView):
    """View to list all billing events."""
    model = EventoFacturacion
    template_name = 'monitor/evento_list.html'
    context_object_name = 'eventos'
    paginate_by = 20
    
    def get_queryset(self):
        qs = super().get_queryset().select_related('porcion', 'ciclo').order_by('-fecha', '-created_at')
        
        # Determine filter values
        self.tipo_filter = self.request.GET.get('tipo', '')
        self.porcion_filter = self.request.GET.get('porcion', '')
        self.ciclo_filter = self.request.GET.get('ciclo', '') # Default to empty string (means "Current" in UI logic, or handle here)
        
        # Filter by tipo_evento if specified
        if self.tipo_filter:
            qs = qs.filter(tipo_evento=self.tipo_filter)
        
        # Filter by porcion if specified
        if self.porcion_filter:
            qs = qs.filter(porcion_id=self.porcion_filter)
            
        # Filter by Cycle
        if self.ciclo_filter == 'all':
            # No filtering, show all history
            pass
        elif self.ciclo_filter and self.ciclo_filter.isdigit():
            # Specific cycle ID
            qs = qs.filter(ciclo_id=self.ciclo_filter)
        else:
            # Default: Current Month/Year (if no filter or explicit empty)
            # Or should we default to "All" if nothing selected?
            # User request: "por defecto muestra solo el ciclo de facturación actual"
            now = timezone.now()
            qs = qs.filter(ciclo__mes=now.month, ciclo__anio=now.year)
            # Update filter for context to reflect "default state" if needed, 
            # but usually empty string in select matches the default option.
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Import here to avoid circular or early import issues if any, though top-level is fine usually.
        # But 'CicloFacturacion' needs to be imported at top level ideally.
        from ..models import CicloFacturacion
        
        context['tipo_filter'] = self.tipo_filter
        context['porcion_filter'] = self.porcion_filter
        context['ciclo_filter'] = self.ciclo_filter
        
        context['porciones'] = Porcion.objects.all().order_by('nombre')
        context['ciclos'] = CicloFacturacion.objects.all() # Ordered by default meta (-anio, -mes)
        
        return context



@admin_required_method
class EventoCreateView(View):
    """View to create billing events."""
    
    def get(self, request):
        form = EventoFacturacionForm()
        return render(request, 'monitor/evento_form.html', {'form': form})
    
    def post(self, request):
        form = EventoFacturacionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Evento de facturación creado exitosamente.')
            return redirect('evento_list')
        return render(request, 'monitor/evento_form.html', {'form': form})


@admin_required_method
class EventoUpdateView(View):
    """View to update billing events."""
    
    def get(self, request, pk):
        evento = get_object_or_404(EventoFacturacion, pk=pk)
        form = EventoFacturacionForm(instance=evento)
        return render(request, 'monitor/evento_form.html', {
            'form': form,
            'evento': evento
        })
    
    def post(self, request, pk):
        evento = get_object_or_404(EventoFacturacion, pk=pk)
        form = EventoFacturacionForm(request.POST, instance=evento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Evento actualizado exitosamente.')
            return redirect('evento_list')
        return render(request, 'monitor/evento_form.html', {
            'form': form,
            'evento': evento
        })


@admin_required_method
class EventoDeleteView(View):
    """View to delete billing events."""
    
    def post(self, request, pk):
        evento = get_object_or_404(EventoFacturacion, pk=pk)
        evento.delete()
        messages.success(request, 'Evento eliminado exitosamente.')
        return redirect('calendario')


# ==================== PORTION MANAGEMENT VIEWS ====================

@admin_required_method
class PorcionListView(ListView):
    """View to list all billing portions."""
    model = Porcion
    template_name = 'monitor/porcion_list.html'
    context_object_name = 'porciones'
    paginate_by = 20
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        # Filter by type if specified
        tipo = self.request.GET.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipo_filter'] = self.request.GET.get('tipo', '')
        return context


@admin_required_method
class PorcionCreateView(View):
    """View to create portions."""
    
    def get(self, request):
        form = PorcionForm()
        return render(request, 'monitor/porcion_form.html', {'form': form})
    
    def post(self, request):
        form = PorcionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Porción creada exitosamente.')
            return redirect('porcion_list')
        return render(request, 'monitor/porcion_form.html', {'form': form})


@admin_required_method
class PorcionUpdateView(View):
    """View to update portions."""
    
    def get(self, request, pk):
        porcion = get_object_or_404(Porcion, pk=pk)
        form = PorcionForm(instance=porcion)
        return render(request, 'monitor/porcion_form.html', {
            'form': form,
            'porcion': porcion
        })
    
    def post(self, request, pk):
        porcion = get_object_or_404(Porcion, pk=pk)
        form = PorcionForm(request.POST, instance=porcion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Porción actualizada exitosamente.')
            return redirect('porcion_list')
        return render(request, 'monitor/porcion_form.html', {
            'form': form,
            'porcion': porcion
        })


@admin_required_method
class PorcionDeleteView(View):
    """View to delete portions."""
    
    def post(self, request, pk):
        porcion = get_object_or_404(Porcion, pk=pk)
        porcion.delete()
        messages.success(request, 'Porción eliminada exitosamente.')
        return redirect('porcion_list')


class ReporteFacturacionView(TemplateView):
    template_name = 'monitor/reporte_facturacion.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get specific date filter or default to current date
        now = timezone.now()
        fecha_param = self.request.GET.get('fecha')
        
        if fecha_param:
            try:
                from datetime import datetime
                fecha_filtro = datetime.strptime(fecha_param, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                fecha_filtro = now.date()
        else:
            # Default to today's date
            fecha_filtro = now.date()
        
        # Get month and year from the filtered date
        mes = fecha_filtro.month
        anio = fecha_filtro.year
        
        context['mes'] = mes
        context['anio'] = anio
        context['fecha_actual'] = fecha_filtro.strftime('%Y-%m-%d')
        
        # Navigation
        if mes == 1:
            context['prev_mes'] = 12
            context['prev_anio'] = anio - 1
        else:
            context['prev_mes'] = mes - 1
            context['prev_anio'] = anio
            
        if mes == 12:
            context['next_mes'] = 1
            context['next_anio'] = anio + 1
        else:
            context['next_mes'] = mes + 1
            context['next_anio'] = anio

        # Month Name in Spanish
        meses = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        context['mes_nombre'] = meses.get(mes, '')

        # Get Billing Events for the specific date only
        events = EventoFacturacion.objects.filter(
            fecha=fecha_filtro,
            tipo_evento='FACTURACION'
        ).select_related('porcion').order_by('fecha')
        
        # Brands Header
        brand_headers = [{'id': c[0], 'name': c[1]} for c in Medidor.MARCA_CHOICES]
        context['brand_headers'] = brand_headers
        
        report_data = []
        dates = sorted(list(set(e.fecha for e in events)))
        
        for d in dates:
            day_events = [e for e in events if e.fecha == d]
            portions = [e.porcion for e in day_events]
            
            # Subquery for last failure
            last_failure = HistorialDisponibilidad.objects.filter(
                equipo=OuterRef('pk'),
                estado='OFFLINE'
            ).order_by('-timestamp').values('timestamp')[:1]

            qs = Equipo.objects.filter(
                medidores_asociados__porcion__in=portions
            ).distinct().annotate(
                total_medidores=Count('medidores_asociados', distinct=True),
                last_failure_time=Subquery(last_failure)
            )
            
            # Dynamic annotations for brands
            annotations = {}
            for code, name in Medidor.MARCA_CHOICES:
                annotations[f'count_{code}'] = Count('medidores_asociados', filter=Q(medidores_asociados__marca=code))
            
            qs = qs.annotate(**annotations).select_related('marca', 'tipo')
            
            equipos_list = []
            for eq in qs:
                # Process annotations into a list for template iteration
                branding_counts = []
                for code, name in Medidor.MARCA_CHOICES:
                    val = getattr(eq, f'count_{code}', 0)
                    branding_counts.append(val)
                eq.brand_counts_list = branding_counts
                equipos_list.append(eq)
                
            report_data.append({
                'date': d,
                'portions': portions,
                'equipments': equipos_list
            })
            
        context['report_data'] = report_data
        return context
