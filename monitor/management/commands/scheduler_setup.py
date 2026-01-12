from django.core.management.base import BaseCommand
from django_q.models import Schedule
from monitor.models import ConfiguracionGlobal

class Command(BaseCommand):
    help = 'Setup the polling schedule'

    def handle(self, *args, **options):
        # Get config
        config = ConfiguracionGlobal.load()
        interval = config.tiempo_interrogacion
        
        # Create or Update schedule
        # We use a schedule name to identify it
        schedule, created = Schedule.objects.get_or_create(
            func='monitor.tasks.poll_devices',
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': interval / 60 if interval >= 60 else 1, # Django Q minutes schedule minimum is 1?
                # Actually specific seconds using CRON or custom logic might be needed for sub-minute.
                # But Schedule.MINUTES is simplest. If < 60s needed, Schedule.CRON or loop task is better.
                # For now let's use type=MINUTES. Or we can use ONCE and Reschedule?
            }
        )
        
        # If we need seconds precision, we might need a different approach or Cron.
        # But users Config is in seconds.
        # If seconds < 60, we might need a loop or multiple schedules?
        # Let's assume 1 minute minimum for now or use Cron with seconds?
        # Django-Q Schedule.CRON doesn't support seconds usually.
        # But `schedule_type='I'` (Minutes) takes integer.
        # Use Schedule.HOURLY, MINUTES, etc.
        
        # For strict seconds interval, we often use a loop management command OR `schedule_type=Schedule.ONCE` and have the task schedule the next one.
        # But that's complex. Let's stick to 1 minute polling as baseline, warning if less.
        
        if interval < 60:
            self.stdout.write(self.style.WARNING(f"Interval {interval}s is less than 60s. Defaulting to 1 minute schedule or custom looper needed."))
        
        schedule.schedule_type = Schedule.MINUTES
        schedule.minutes = max(1, interval / 60)
        schedule.save()
        
        self.stdout.write(self.style.SUCCESS('Schedule setup complete.'))
