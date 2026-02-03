"""
Management command to send test alert notifications.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from monitor.services.alert_service import AlertService
from monitor.models import Equipo
import random


class Command(BaseCommand):
    help = 'Send test alert notifications (Email and Telegram)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=1,
            help='Number of test alerts to send (default: 1)'
        )
        parser.add_argument(
            '--email-only',
            action='store_true',
            help='Send only email notifications'
        )
        parser.add_argument(
            '--telegram-only',
            action='store_true',
            help='Send only Telegram notifications'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=0,
            help='Delay in seconds between alerts (default: 0)'
        )

    def handle(self, *args, **options):
        count = options['count']
        delay = options['delay']
        email_only = options['email_only']
        telegram_only = options['telegram_only']
        
        # Determine channels
        if email_only:
            channels = ['email']
        elif telegram_only:
            channels = ['telegram']
        else:
            channels = ['email', 'telegram']
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"Sending {count} test alert notification(s)...")
        self.stdout.write(f"Channels: {', '.join(channels)}")
        self.stdout.write("="*60 + "\n")
        
        for i in range(count):
            if count > 1:
                self.stdout.write(f"\n📨 Sending test alert {i+1}/{count}...\n")
            
            # Create mock equipment data for testing
            test_equipment_data = self._create_test_data(i+1)
            
            try:
                result = {}
                
                # Send email if requested
                if 'email' in channels:
                    email_result = AlertService.send_email_alert(test_equipment_data)
                    result['email'] = email_result
                    if email_result:
                        self.stdout.write(self.style.SUCCESS("  ✓ Email notification sent"))
                    else:
                        self.stdout.write(self.style.WARNING("  ⚠ Email notification failed"))
                
                # Send Telegram if requested
                if 'telegram' in channels:
                    telegram_result = AlertService.send_telegram_alert(test_equipment_data)
                    result['telegram'] = telegram_result
                    
                    if telegram_result.get('success'):
                        sent_count = telegram_result.get('sent_count', 0)
                        self.stdout.write(self.style.SUCCESS(
                            f"  ✓ Telegram notification sent to {sent_count} recipient(s)"
                        ))
                    else:
                        error = telegram_result.get('error', 'Unknown error')
                        self.stdout.write(self.style.WARNING(
                            f"  ⚠ Telegram notification failed: {error}"
                        ))
                
                # Delay between alerts if specified
                if delay > 0 and i < count - 1:
                    import time
                    self.stdout.write(f"  ⏳ Waiting {delay} seconds...")
                    time.sleep(delay)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"✓ Completed sending {count} test alert(s)"))
        self.stdout.write("="*60 + "\n")
        
        self.stdout.write("\n💡 Tips:")
        self.stdout.write("  - Check your email inbox")
        self.stdout.write("  - Check your Telegram for messages from @msj_qawaq_bot")
        self.stdout.write("  - Review logs if messages weren't received")

    def _create_test_data(self, test_number):
        """Create mock equipment data for testing."""
        
        # Generate realistic test data
        test_equipment = [
            {
                'equipo': type('obj', (object,), {
                    'id_equipo': f'TEST-EQ-{test_number:03d}',
                    'ip': f'192.168.1.{100 + test_number}',
                    'marca': 'Test Brand',
                    'modelo': 'Test Model',
                })(),
                'downtime': f"{random.randint(1, 5)}h {random.randint(10, 59)}m",
                'medidor_count': random.randint(10, 50),
                'affected_portions': f"Porción Test {test_number}",
            }
            for _ in range(random.randint(1, 3))
        ]
        
        return test_equipment
