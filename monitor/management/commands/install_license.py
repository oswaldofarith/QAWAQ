from django.core.management.base import BaseCommand
from monitor.services.license_service import LicenseService

class Command(BaseCommand):
    help = 'Installs a license key'

    def add_arguments(self, parser):
        parser.add_argument('key', type=str, help='The license key string')

    def handle(self, *args, **options):
        key = options['key']
        
        # Save first
        LicenseService.save_license_file(key)
        
        # Verify
        info = LicenseService.validate_license()
        
        if info.is_valid:
            self.stdout.write(self.style.SUCCESS(f'License installed successfully!'))
            self.stdout.write(f'Client: {info.client_name}')
            self.stdout.write(f'Expires: {info.expiration_date} ({info.days_remaining} days left)')
        else:
            self.stdout.write(self.style.ERROR(f'License installed but invalid: {info.status_message}'))
