
class ReporteFacturacionView(TemplateView):
    template_name = 'monitor/reporte_facturacion.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import EventoFacturacion, Medidor, HistorialDisponibilidad
        from django.db.models import Count, Q, Subquery, OuterRef
        from django.utils import timezone
        import datetime
        
        # Get Month/Year filter or default to current
        now = timezone.now()
        try:
            mes = int(self.request.GET.get('mes', now.month))
            anio = int(self.request.GET.get('anio', now.year))
        except (ValueError, TypeError):
            mes = now.month
            anio = now.year

        context['mes'] = mes
        context['anio'] = anio
        
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

        # Get Billing Events for this month (FACTURACION only)
        events = EventoFacturacion.objects.filter(
            fecha__year=anio,
            fecha__month=mes,
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
