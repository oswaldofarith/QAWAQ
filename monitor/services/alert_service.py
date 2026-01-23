"""
Alert service for monitoring critical equipment status.

Sends email notifications when critical equipment goes offline.
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from monitor.models import Equipo, Medidor
import logging

logger = logging.getLogger(__name__)

# Import Telegram service with graceful fallback
try:
    from .telegram_service import TelegramNotificationService
except ImportError:
    TelegramNotificationService = None
    logger.warning("TelegramNotificationService not available")


class AlertService:
    """Service for handling equipment alerts."""
    
    @staticmethod
    def get_critical_equipment():
        """
        Get list of equipment that is considered critical.
        
        Critical equipment is defined as:
        - Equipment that affects billing (has associated medidores with billing portions)
        - Or equipment marked as having 'piloto' (critical monitoring points)
        """
        from django.db.models import Q
        
        # Use Q objects to combine conditions in a single query
        critical_equipment = Equipo.objects.filter(
            Q(medidores_asociados__porcion__isnull=False) |
            Q(piloto__isnull=False) & ~Q(piloto='')
        ).distinct()
        
        return critical_equipment
    
    @staticmethod
    def get_offline_equipment(threshold_minutes=None):
        """
        Get equipment that is currently offline.
        
        Args:
            threshold_minutes: Minutes equipment must be offline before alerting
                             If None, uses ALERT_OFFLINE_THRESHOLD from settings
        
        Returns:
            QuerySet of offline Equipo objects
        """
        if threshold_minutes is None:
            threshold_minutes = settings.ALERT_OFFLINE_THRESHOLD
        
        threshold_time = timezone.now() - timedelta(minutes=threshold_minutes)
        
        offline_equipment = Equipo.objects.filter(
            is_online=False,
            last_seen__isnull=False,
            last_seen__lt=threshold_time
        )
        
        return offline_equipment
    
    @staticmethod
    def get_critical_offline_equipment():
        """Get critical equipment that is currently offline."""
        from django.db.models import Q
        
        # Get critical equipment using a single query with Q objects
        critical = Equipo.objects.filter(
            Q(medidores_asociados__porcion__isnull=False) |
            (Q(piloto__isnull=False) & ~Q(piloto=''))
        ).distinct()
        
        offline = AlertService.get_offline_equipment()
        
        # Return intersection using filter
        return critical.filter(pk__in=offline.values_list('pk', flat=True))
    
    @staticmethod
    def prepare_equipment_data(equipment_list):
        """
        Prepare equipment data for notifications.
        
        Args:
            equipment_list: List or QuerySet of Equipo objects
        
        Returns:
            list: Prepared equipment data dictionaries
        """
        equipment_data = []
        for equipo in equipment_list:
            # Calculate downtime
            downtime = None
            if equipo.last_seen:
                downtime = timezone.now() - equipo.last_seen
                hours, remainder = divmod(downtime.total_seconds(), 3600)
                minutes = remainder // 60
                downtime_str = f"{int(hours)}h {int(minutes)}m"
            else:
                downtime_str = "Unknown"
            
            # Count associated medidores
            medidor_count = equipo.medidores_asociados.count()
            
            # Get affected portions
            portions = equipo.medidores_asociados.values_list(
                'porcion__nombre', flat=True
            ).distinct()
            portions_str = ', '.join(filter(None, portions)) or 'N/A'
            
            equipment_data.append({
                'equipo': equipo,
                'downtime': downtime_str,
                'medidor_count': medidor_count,
                'affected_portions': portions_str,
            })
        
        return equipment_data
    
    @staticmethod
    def send_email_alert(equipment_data):
        """
        Send email alert for offline equipment.
        
        Args:
            equipment_data: List of equipment data dictionaries from prepare_equipment_data
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not equipment_data:
            logger.info("No equipment data to email")
            return False
        
        # Render email content
        context = {
            'equipment_list': equipment_data,
            'alert_time': timezone.now(),
            'total_count': len(equipment_data),
        }
        
        html_message = render_to_string(
            'monitor/emails/equipment_alert.html',
            context
        )
        
        # Plain text fallback
        text_message = f"""
ALERTA: Equipos Críticos OFFLINE - QAWAQ

Se detectaron {len(equipment_data)} equipos críticos offline:

"""
        for item in equipment_data:
            text_message += f"- {item['equipo'].id_equipo} ({item['equipo'].ip})\n"
            text_message += f"  Tiempo offline: {item['downtime']}\n"
            text_message += f"  Medidores afectados: {item['medidor_count']}\n"
            text_message += f"  Porciones: {item['affected_portions']}\n\n"
        
        text_message += f"\nFecha de alerta: {timezone.now().strftime('%d/%m/%Y %H:%M')}\n"
        
        # Send email
        try:
            send_mail(
                subject=f'⚠️ ALERTA: {len(equipment_data)} Equipo(s) Crítico(s) OFFLINE',
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin[1] for admin in settings.ADMINS],
                fail_silently=False,
                html_message=html_message,
            )
            logger.info(f"Alert email sent for {len(equipment_data)} equipment")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
            return False
    
    @staticmethod
    def send_telegram_alert(equipment_data):
        """
        Send Telegram alert for offline equipment.
        
        Args:
            equipment_data: List of equipment data dictionaries
        
        Returns:
            dict: Result summary from Telegram service
        """
        if not equipment_data:
            logger.info("No equipment data to send via Telegram")
            return {'success': False, 'sent_count': 0}
        
        if TelegramNotificationService is None:
            logger.warning("Telegram service not available")
            return {'success': False, 'sent_count': 0, 'error': 'Service not available'}
        
        telegram_service = TelegramNotificationService()
        result = telegram_service.send_critical_alert(equipment_data)
        
        if result.get('success'):
            logger.info(f"Telegram alerts sent to {result.get('sent_count')} recipients")
        else:
            logger.warning(f"Telegram alert failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    @staticmethod
    def send_equipment_alert(equipment_list, channels=None):
        """
        Send multi-channel alert for offline equipment.
        
        Args:
            equipment_list: List or QuerySet of Equipo objects
            channels: List of channels to use ['email', 'telegram']. If None, uses both.
        
        Returns:
            dict: Summary of alerts sent across all channels
        """
        if not equipment_list:
            logger.info("No equipment to alert about")
            return {'email': False, 'telegram': {'success': False, 'sent_count': 0}}
        
        # Default to both channels if not specified
        if channels is None:
            channels = ['email', 'telegram']
        
        # Prepare equipment data once for both channels
        equipment_data = AlertService.prepare_equipment_data(equipment_list)
        
        result = {}
        
        # Send email if requested
        if 'email' in channels:
            result['email'] = AlertService.send_email_alert(equipment_data)
        
        # Send Telegram if requested
        if 'telegram' in channels:
            result['telegram'] = AlertService.send_telegram_alert(equipment_data)
        
        return result
    
    @staticmethod
    def check_and_alert():
        """
        Main method to check for offline critical equipment and send alerts.
        
        This should be called periodically by Django-Q or cron.
        
        Returns:
            dict: Summary of alert check
        """
        critical_offline = AlertService.get_critical_offline_equipment()
        equipment_list = list(critical_offline)
        
        result = {
            'checked_at': timezone.now(),
            'critical_count': AlertService.get_critical_equipment().count(),
            'offline_critical_count': len(equipment_list),
            'email_sent': False,
            'telegram_sent': False,
            'telegram_recipients': 0,
        }
        
        if equipment_list:
            alert_result = AlertService.send_equipment_alert(equipment_list)
            result['email_sent'] = alert_result.get('email', False)
            
            telegram_result = alert_result.get('telegram', {})
            result['telegram_sent'] = telegram_result.get('success', False)
            result['telegram_recipients'] = telegram_result.get('sent_count', 0)
            
            result['equipment_ids'] = [e.id_equipo for e in equipment_list]
        
        logger.info(f"Alert check completed: {result}")
        return result
