from django.core.management.base import BaseCommand
from monitor.services.license_service import LicenseService

class Command(BaseCommand):
    help = 'Verifies the current license status'

    def handle(self, *args, **options):
        info = LicenseService.validate_license()
        
        if info.is_valid:
            self.stdout.write(self.style.SUCCESS(f'License Valid'))
            self.stdout.write(f'Client: {info.client_name}')
            self.stdout.write(f'Email: {info.email}')
            self.stdout.write(f'Expires: {info.expiration_date}')
            self.stdout.write(f'Remaining: {info.days_remaining} days')
            
            if info.days_remaining < 7:
                self.stdout.write(self.style.WARNING('WARNING: License expires soon!'))
        else:
            self.stdout.write(self.style.ERROR(f'License Invalid'))
            self.stdout.write(f'Status: {info.status_message}')
