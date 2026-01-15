"""
Django management command to check for critical offline equipment.

This command should be run periodically (e.g., every 15 minutes) via cron or Django-Q.

Usage:
    python manage.py check_equipment_alerts
"""
from django.core.management.base import BaseCommand
from monitor.services.alert_service import AlertService


class Command(BaseCommand):
    help = 'Check for critical offline equipment and send alerts'

    def handle(self, *args, **options):
        self.stdout.write('Checking for critical offline equipment...')
        
        result = AlertService.check_and_alert()
        
        self.stdout.write(f"Checked at: {result['checked_at']}")
        self.stdout.write(f"Total critical equipment: {result['critical_count']}")
        self.stdout.write(f"Critical equipment offline: {result['offline_critical_count']}")
        
        if result['offline_critical_count'] > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Found {result['offline_critical_count']} critical equipment offline"
                )
            )
            self.stdout.write(f"Equipment IDs: {', '.join(result.get('equipment_ids', []))}")
            
            if result['alert_sent']:
                self.stdout.write(self.style.SUCCESS('✓ Alert email sent successfully'))
            else:
                self.stdout.write(self.style.ERROR('✗ Failed to send alert email'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ All critical equipment is online'))
