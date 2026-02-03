"""
Management command to setup Django-Q scheduled task for equipment alerts.
"""
from django.core.management.base import BaseCommand
from django_q.models import Schedule


class Command(BaseCommand):
    help = 'Setup Django-Q scheduled task for checking equipment alerts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=15,
            help='Check interval in minutes (default: 15)'
        )
        parser.add_argument(
            '--remove',
            action='store_true',
            help='Remove existing schedule instead of creating'
        )

    def handle(self, *args, **options):
        schedule_name = 'Check Critical Equipment Alerts'
        interval = options['interval']
        
        # Check if schedule already exists
        existing = Schedule.objects.filter(name=schedule_name).first()
        
        if options['remove']:
            if existing:
                existing.delete()
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Removed scheduled task: {schedule_name}'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    '⚠ No scheduled task found to remove'
                ))
            return
        
        if existing:
            self.stdout.write(self.style.WARNING(
                f'⚠ Scheduled task already exists: {schedule_name}'
            ))
            self.stdout.write(f'  - Interval: Every {existing.minutes} minutes')
            self.stdout.write(f'  - Status: {"Active" if existing.repeats != 0 else "Inactive"}')
            self.stdout.write(f'  - Next run: {existing.next_run if existing.next_run else "Not scheduled"}')
            self.stdout.write('\nTo remove the existing task, run:')
            self.stdout.write(self.style.SUCCESS('  python manage.py setup_alert_schedule --remove'))
            return
        
        # Create new schedule
        try:
            schedule = Schedule.objects.create(
                name=schedule_name,
                func='monitor.management.commands.check_equipment_alerts.Command.handle',
                schedule_type=Schedule.MINUTES,
                minutes=interval,
                repeats=-1,  # Repeat indefinitely
            )
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Successfully created scheduled task!'
            ))
            self.stdout.write(f'\n  Task Name: {schedule.name}')
            self.stdout.write(f'  Interval: Every {interval} minutes')
            self.stdout.write(f'  Function: {schedule.func}')
            self.stdout.write(f'  Status: Active')
            
            self.stdout.write(f'\n📋 The system will now automatically check for critical')
            self.stdout.write(f'   equipment failures every {interval} minutes.')
            
            self.stdout.write(f'\n💡 Tips:')
            self.stdout.write(f'  - View scheduled tasks: /admin/django_q/schedule/')
            self.stdout.write(f'  - View task history: /admin/django_q/success/ or /admin/django_q/failure/')
            self.stdout.write(f'  - Ensure qcluster is running: python manage.py qcluster')
            
            self.stdout.write(f'\n🔧 To change the interval, remove this task and create a new one:')
            self.stdout.write(self.style.SUCCESS(
                f'  python manage.py setup_alert_schedule --remove'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'  python manage.py setup_alert_schedule --interval 30'
            ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Failed to create scheduled task: {e}'))
            self.stdout.write('\nPossible issues:')
            self.stdout.write('  - Django-Q not installed')
            self.stdout.write('  - Database connection issue')
            self.stdout.write('  - Invalid function path')
