from django.shortcuts import render, redirect
from django.urls import reverse
from monitor.services.license_service import LicenseService

class LicenseEnforcerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow access to admin, login, static files, and the license expired page itself
        path = request.path
        if (path.startswith('/admin/') or 
            path.startswith('/login/') or 
            path.startswith('/static/') or 
            path.startswith('/media/') or
            path == '/license-expired/'):
            return self.get_response(request)

        # Check license
        info = LicenseService.validate_license()
        
        if not info.is_valid:
            # If invalid, render the expiration page directly or redirect
            # Passing info context to show why (Expired vs Missing)
            return render(request, 'monitor/license_expired.html', {'info': info}, status=403)

        # Add license info to request context (optional, for showing "5 days left" in UI)
        request.license_info = info
        
        response = self.get_response(request)
        return response
