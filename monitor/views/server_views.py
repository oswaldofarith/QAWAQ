from django.views.generic import ListView
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..models import Sistema, Servidor
from ..forms import SistemaForm, ServidorForm
from ..decorators import login_required_method, admin_required_method

@login_required_method
class ServidorListView(ListView):
    """Listado de servidores agrupados por Sistema."""
    model = Sistema
    template_name = 'monitor/servidor_list.html'
    context_object_name = 'sistemas'
    
    def get_queryset(self):
        # Fetch systems with their servers prefeched
        return Sistema.objects.prefetch_related('servidores').all()

@admin_required_method
class SistemaCreateView(View):
    def get(self, request):
        form = SistemaForm()
        return render(request, 'monitor/sistema_form.html', {'form': form})
    
    def post(self, request):
        form = SistemaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sistema creado exitosamente.')
            return redirect('servidor_list')
        return render(request, 'monitor/sistema_form.html', {'form': form})

@admin_required_method
class SistemaUpdateView(View):
    def get(self, request, pk):
        sistema = get_object_or_404(Sistema, pk=pk)
        form = SistemaForm(instance=sistema)
        return render(request, 'monitor/sistema_form.html', {'form': form, 'sistema': sistema})
    
    def post(self, request, pk):
        sistema = get_object_or_404(Sistema, pk=pk)
        form = SistemaForm(request.POST, instance=sistema)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sistema actualizado exitosamente.')
            return redirect('servidor_list')
        return render(request, 'monitor/sistema_form.html', {'form': form, 'sistema': sistema})

@admin_required_method
class SistemaDeleteView(View):
    def post(self, request, pk):
        sistema = get_object_or_404(Sistema, pk=pk)
        sistema.delete()
        messages.success(request, 'Sistema eliminado exitosamente.')
        return redirect('servidor_list')

@admin_required_method
class ServidorCreateView(View):
    def get(self, request):
        initial_sistema = request.GET.get('sistema')
        form = ServidorForm(initial={'sistema': initial_sistema} if initial_sistema else None)
        return render(request, 'monitor/servidor_form.html', {'form': form})
    
    def post(self, request):
        form = ServidorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servidor creado exitosamente.')
            return redirect('servidor_list')
        return render(request, 'monitor/servidor_form.html', {'form': form})

@admin_required_method
class ServidorUpdateView(View):
    def get(self, request, pk):
        servidor = get_object_or_404(Servidor, pk=pk)
        form = ServidorForm(instance=servidor)
        return render(request, 'monitor/servidor_form.html', {'form': form, 'servidor': servidor})
    
    def post(self, request, pk):
        servidor = get_object_or_404(Servidor, pk=pk)
        form = ServidorForm(request.POST, instance=servidor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servidor actualizado exitosamente.')
            return redirect('servidor_list')
        return render(request, 'monitor/servidor_form.html', {'form': form, 'servidor': servidor})

@admin_required_method
class ServidorDeleteView(View):
    def post(self, request, pk):
        servidor = get_object_or_404(Servidor, pk=pk)
        servidor.delete()
        messages.success(request, 'Servidor eliminado exitosamente.')
        return redirect('servidor_list')
