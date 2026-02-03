from django.views.generic import ListView
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count

from ..models import ConfiguracionGlobal, Marca, TipoEquipo
from ..forms import ConfiguracionGlobalForm, MarcaForm, TipoEquipoForm
from ..decorators import admin_required_method

@admin_required_method  
class ConfiguracionView(View):
    """View to display and edit global system configuration."""
    
    def get(self, request):
        config = ConfiguracionGlobal.load()
        form = ConfiguracionGlobalForm(instance=config)
        
        # Check Telegram configuration status
        from django.conf import settings
        telegram_enabled = getattr(settings, 'TELEGRAM_ENABLED', False) and bool(getattr(settings, 'TELEGRAM_BOT_TOKEN', ''))
        telegram_bot_info = None
        
        if telegram_enabled:
            try:
                from monitor.services.telegram_service import TelegramNotificationService
                telegram_service = TelegramNotificationService()
                bot_result = telegram_service.verify_bot_connection()
                if bot_result.get('success'):
                    telegram_bot_info = bot_result
            except Exception:
                pass
        
        return render(request, 'monitor/configuracion.html', {
            'form': form,
            'config': config,
            'telegram_enabled': telegram_enabled,
            'telegram_bot_info': telegram_bot_info
        })
    
    def post(self, request):
        config = ConfiguracionGlobal.load()
        form = ConfiguracionGlobalForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración actualizada exitosamente.')
            return redirect('configuracion')
        return render(request, 'monitor/configuracion.html', {
            'form': form,
            'config': config
        })

@admin_required_method
class MarcaListView(ListView):
    """List all equipment brands with equipment count."""
    model = Marca
    template_name = 'monitor/marca_list.html'
    context_object_name = 'marcas'
    
    def get_queryset(self):
        queryset = Marca.objects.annotate(
            equipment_count=Count('equipo')
        ).order_by('nombre')
        
        search = self.request.GET.get('q', '')
        if search:
            queryset = queryset.filter(nombre__icontains=search)
        
        return queryset


@admin_required_method
class MarcaCreateView(View):
    """Create a new brand."""
    
    def get(self, request):
        form = MarcaForm()
        return render(request, 'monitor/marca_form.html', {
            'form': form,
            'title': 'Nueva Marca',
            'is_create': True
        })
    
    def post(self, request):
        form = MarcaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Marca "{form.cleaned_data["nombre"]}" creada exitosamente.')
            return redirect('marca_list')
        return render(request, 'monitor/marca_form.html', {
            'form': form,
            'title': 'Nueva Marca',
            'is_create': True
        })


@admin_required_method
class MarcaUpdateView(View):
    """Update an existing brand."""
    
    def get(self, request, pk):
        marca = get_object_or_404(Marca, pk=pk)
        form = MarcaForm(instance=marca)
        return render(request, 'monitor/marca_form.html', {
            'form': form,
            'marca': marca,
            'title': 'Editar Marca',
            'is_create': False
        })
    
    def post(self, request, pk):
        marca = get_object_or_404(Marca, pk=pk)
        form = MarcaForm(request.POST, instance=marca)
        if form.is_valid():
            form.save()
            messages.success(request, f'Marca "{marca.nombre}" actualizada exitosamente.')
            return redirect('marca_list')
        return render(request, 'monitor/marca_form.html', {
            'form': form,
            'marca': marca,
            'title': 'Editar Marca',
            'is_create': False
        })


@admin_required_method
class MarcaDeleteView(View):
    """Delete a brand (with protection if equipment exists)."""
    
    def get(self, request, pk):
        marca = get_object_or_404(Marca, pk=pk)
        equipment_count = marca.equipo_set.count()
        return render(request, 'monitor/marca_confirm_delete.html', {
            'marca': marca,
            'equipment_count': equipment_count
        })
    
    def post(self, request, pk):
        marca = get_object_or_404(Marca, pk=pk)
        equipment_count = marca.equipo_set.count()
        
        if equipment_count > 0:
            messages.error(request, f'No se puede eliminar la marca "{marca.nombre}" porque tiene {equipment_count} equipo(s) asignado(s).')
            return redirect('marca_list')
        
        nombre = marca.nombre
        marca.delete()
        messages.success(request, f'Marca "{nombre}" eliminada exitosamente.')
        return redirect('marca_list')


@admin_required_method
class TipoEquipoListView(ListView):
    """List all equipment types with equipment count."""
    model = TipoEquipo
    template_name = 'monitor/tipoequipo_list.html'
    context_object_name = 'tipos'
    
    def get_queryset(self):
        queryset = TipoEquipo.objects.annotate(
            equipment_count=Count('equipo')
        ).order_by('nombre')
        
        search = self.request.GET.get('q', '')
        if search:
            queryset = queryset.filter(nombre__icontains=search)
        
        return queryset


@admin_required_method
class TipoEquipoCreateView(View):
    """Create a new equipment type."""
    
    def get(self, request):
        form = TipoEquipoForm()
        return render(request, 'monitor/tipoequipo_form.html', {
            'form': form,
            'title': 'Nuevo Tipo de Equipo',
            'is_create': True
        })
    
    def post(self, request):
        form = TipoEquipoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Tipo "{form.cleaned_data["nombre"]}" creado exitosamente.')
            return redirect('tipo_list')
        return render(request, 'monitor/tipoequipo_form.html', {
            'form': form,
            'title': 'Nuevo Tipo de Equipo',
            'is_create': True
        })


@admin_required_method
class TipoEquipoUpdateView(View):
    """Update an existing equipment type."""
    
    def get(self, request, pk):
        tipo = get_object_or_404(TipoEquipo, pk=pk)
        form = TipoEquipoForm(instance=tipo)
        return render(request, 'monitor/tipoequipo_form.html', {
            'form': form,
            'tipo': tipo,
            'title': 'Editar Tipo de Equipo',
            'is_create': False
        })
    
    def post(self, request, pk):
        tipo = get_object_or_404(TipoEquipo, pk=pk)
        form = TipoEquipoForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            messages.success(request, f'Tipo "{tipo.nombre}" actualizado exitosamente.')
            return redirect('tipo_list')
        return render(request, 'monitor/tipoequipo_form.html', {
            'form': form,
            'tipo': tipo,
            'title': 'Editar Tipo de Equipo',
            'is_create': False
        })


@admin_required_method
class TipoEquipoDeleteView(View):
    """Delete an equipment type (with protection if equipment exists)."""
    
    def get(self, request, pk):
        tipo = get_object_or_404(TipoEquipo, pk=pk)
        equipment_count = tipo.equipo_set.count()
        return render(request, 'monitor/tipoequipo_confirm_delete.html', {
            'tipo': tipo,
            'equipment_count': equipment_count
        })
    
    def post(self, request, pk):
        tipo = get_object_or_404(TipoEquipo, pk=pk)
        equipment_count = tipo.equipo_set.count()
        
        if equipment_count > 0:
            messages.error(request, f'No se puede eliminar el tipo "{tipo.nombre}" porque tiene {equipment_count} equipo(s) asignado(s).')
            return redirect('tipo_list')
        
        nombre = tipo.nombre
        tipo.delete()
        messages.success(request, f'Tipo "{nombre}" eliminado exitosamente.')
        return redirect('tipo_list')
