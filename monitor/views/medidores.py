from django.views.generic import ListView
from django.views import View
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import pandas as pd
import openpyxl

from ..models import Medidor, Equipo, Porcion, Marca
from ..decorators import admin_required_method

@admin_required_method
class MedidorListView(ListView):
    """View to list all AMI meters (read-only)."""
    model = Medidor
    template_name = 'monitor/medidor_list.html'
    context_object_name = 'medidores'
    paginate_by = 50
    
    def get_queryset(self):
        qs = super().get_queryset().select_related('porcion', 'colector')
        
        # Filter by marca if specified
        marca = self.request.GET.get('marca')
        if marca:
            qs = qs.filter(marca=marca)
        
        # Filter by porcion if specified
        porcion_id = self.request.GET.get('porcion')
        if porcion_id:
            qs = qs.filter(porcion_id=porcion_id)
        
        # Search by numero
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(numero__icontains=search)
        
        # Filter by colector if specified
        colector_filter = self.request.GET.get('colector')
        if colector_filter:
            colector_filter = colector_filter.strip()
            if colector_filter.lower() == 'sin_asignar':
                qs = qs.filter(colector__isnull=True)
            elif colector_filter:
                # Look up colector by id_equipo
                qs = qs.filter(colector__id_equipo=colector_filter)
        
        return qs.order_by('numero')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['marca_filter'] = self.request.GET.get('marca', '')
        context['porcion_filter'] = self.request.GET.get('porcion', '')
        context['colector_filter'] = self.request.GET.get('colector', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['porciones'] = Porcion.objects.all().order_by('nombre')
        context['marcas'] = Medidor.MARCA_CHOICES
        context['colectores'] = Equipo.objects.all().order_by('id_equipo')
        
        # Get brand colors from Marca model for dynamic badge coloring
        marca_colors = {}
        for marca in Marca.objects.all():
            marca_colors[marca.nombre.upper()] = marca.color
        context['marca_colors'] = marca_colors
        
        # Count statistics
        total = Medidor.objects.count()
        honeywell = Medidor.objects.filter(marca='HONEYWELL').count()
        trilliant = Medidor.objects.filter(marca='TRILLIANT').count()
        itron = Medidor.objects.filter(marca='ITRON').count()
        hexing = Medidor.objects.filter(marca='HEXING').count()
        
        # Format numbers with thousand separators (dots)
        context['total_medidores'] = f"{total:,}".replace(',', '.')
        context['stats'] = {
            'honeywell': {
                'count': f"{honeywell:,}".replace(',', '.'),
                'color': marca_colors.get('HONEYWELL', '#0dcaf0')  # Default fallback to info color
            },
            'trilliant': {
                'count': f"{trilliant:,}".replace(',', '.'),
                'color': marca_colors.get('TRILLIANT', '#ffc107')  # Default fallback to warning color
            },
            'itron': {
                'count': f"{itron:,}".replace(',', '.'),
                'color': marca_colors.get('ITRON', '#198754')  # Default fallback to success color
            },
            'hexing': {
                'count': f"{hexing:,}".replace(',', '.'),
                'color': marca_colors.get('HEXING', '#dc3545')  # Default fallback to danger color
            },
        }
        
        return context

@method_decorator(login_required, name='dispatch')
class ExportMedidoresView(View):
    """View to export filtered medidores to XLSX."""
    
    def get(self, request, *args, **kwargs):
        # 1. Base QuerySet
        qs = Medidor.objects.select_related('porcion', 'colector').all()
        
        # 2. Apply Filters (same logic as MedidorListView)
        
        # Filter by marca
        marca = request.GET.get('marca')
        if marca:
            qs = qs.filter(marca=marca)
        
        # Filter by porcion
        porcion_id = request.GET.get('porcion')
        if porcion_id:
            qs = qs.filter(porcion_id=porcion_id)
        
        # Search by numero
        search = request.GET.get('q')
        if search:
            qs = qs.filter(numero__icontains=search)
        
        # Filter by colector
        colector_filter = request.GET.get('colector')
        if colector_filter:
            colector_filter = colector_filter.strip()
            if colector_filter.lower() == 'sin_asignar':
                qs = qs.filter(colector__isnull=True)
            elif colector_filter:
                qs = qs.filter(colector__id_equipo=colector_filter)
        
        qs = qs.order_by('numero')
        
        # 3. Prepare Data for DataFrame
        data = []
        for medidor in qs:
            data.append({
                'Número de Medidor': medidor.numero,
                'Marca': medidor.get_marca_display(),
                'Porción': medidor.porcion.nombre if medidor.porcion else '',
                'Tipo Porción': medidor.porcion.get_tipo_display() if medidor.porcion else '',
                'Colector Asociado': medidor.colector.id_equipo if medidor.colector else 'Sin asignar',
                'IP Colector': medidor.colector.ip if medidor.colector else '',
                'Estado Colector': 'Online' if (medidor.colector and medidor.colector.is_online) else 'Offline' if medidor.colector else ''
            })
            
        # 4. Create DataFrame and Export
        if not data:
            data = [{
                'Número de Medidor': '',
                'Marca': '',
                'Porción': '',
                'Tipo Porción': '',
                'Colector Asociado': '',
                'IP Colector': '',
                'Estado Colector': ''
            }] # Provide header at least
        
        df = pd.DataFrame(data)
        if not data[0]['Número de Medidor']: # If dummy data
             df = pd.DataFrame(columns=data[0].keys())

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=medidores_export.xlsx'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Medidores')
            
            # Auto-adjust columns width
            worksheet = writer.sheets['Medidores']
            for column in df:
                # Find max length of column content or column header
                column_length = max(df[column].astype(str).map(len).max(), len(column)) if not df.empty else len(column)
                col_letter = openpyxl.utils.get_column_letter(df.columns.get_loc(column) + 1)
                worksheet.column_dimensions[col_letter].width = column_length + 2
                
        return response
