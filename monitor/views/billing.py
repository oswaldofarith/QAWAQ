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
from ..decorators import login_required_method, admin_required_method

@login_required_method
class CalendarioView(TemplateView):
    """View to display the monthly billing calendar."""
    template_name = 'monitor/calendario.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get year and month from URL or use current
        anio = self.kwargs.get('anio') or date.today().year
        mes = self.kwargs.get('mes') or date.today().month
        
        # Ensure valid month
        mes = max(1, min(12, mes))
        
        context['anio'] = anio
        context['mes'] = mes
        
        # Month names in Spanish
        meses_es = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        context['mes_nombre'] = meses_es[mes]
        
        # Calculate previous/next month
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
        
        # Get calendar data
        cal = calendar.monthcalendar(anio, mes)
        context['calendar'] = cal
        
        # Get all events for this month with portion meter counts
        eventos = EventoFacturacion.objects.filter(
            fecha__year=anio,
            fecha__month=mes,
            tipo_evento='FACTURACION'
        ).select_related('porcion', 'ciclo').annotate(
            medidores_count=Count('porcion__medidores')
        )
        
        # Group events by day
        eventos_por_dia = {}
        for evento in eventos:
            dia = evento.fecha.day
            if dia not in eventos_por_dia:
                eventos_por_dia[dia] = []
            eventos_por_dia[dia].append({
                'id': evento.id,
                'nombre': evento.get_display_name(),
                'color': evento.get_color(),
                'tipo': evento.tipo_evento,
                'porcion': evento.porcion.nombre,
                'porcion_id': evento.porcion.id,
                'medidores_count': evento.medidores_count
            })
        
        context['eventos_por_dia'] = eventos_por_dia
        context['today'] = date.today()
        
        return context


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
