from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import render, redirect
from ..services.license_service import LicenseService

class LicenseSettingsView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'monitor/license_settings.html'
    success_url = reverse_lazy('configuracion_licencia')

    def test_func(self):
        """Ensure only admins can access license settings."""
        return self.request.user.profile.role == 'admin'

    def get_form_class(self):
        from ..license_forms import LicenseUpdateForm
        return LicenseUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Load current license info directly from service to ensure fresh data
        context['license_info'] = LicenseService.validate_license()
        return context

    def form_valid(self, form):
        key = form.cleaned_data['license_key']
        
        # Save the new key
        LicenseService.save_license_file(key)
        
        # Validate the new key immediately
        info = LicenseService.validate_license()
        
        if info.is_valid:
            messages.success(self.request, f"Licencia actualizada correctamente. Cliente: {info.client_name}")
        else:
            messages.error(self.request, f"La licencia instalada no es válida: {info.status_message}")
            
        return super().form_valid(form)
