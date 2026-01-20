from django.core.management.base import BaseCommand
from monitor.services.license_service import LicenseService

class Command(BaseCommand):
    help = 'Generates a signed license key for QAWAQ'

    def add_arguments(self, parser):
        parser.add_argument('--client', type=str, required=True, help='Name of the client')
        parser.add_argument('--days', type=int, required=True, help='Days valid from today')
        parser.add_argument('--email', type=str, default="", help='Contact email for the client')

    def handle(self, *args, **options):
        client = options['client']
        days = options['days']
        email = options['email']

        token = LicenseService.generate_license(client, days, email=email)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully generated license for "{client}"'))
        self.stdout.write(f'\n--- LICENSE KEY START ---\n{token}\n--- LICENSE KEY END ---\n')
        self.stdout.write('Copy the key above and run: python manage.py install_license "KEY"')
