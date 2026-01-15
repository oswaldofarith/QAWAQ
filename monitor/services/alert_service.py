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
        # Get equipment with associated medidores that have billing portions
        equipment_with_billing = Equipo.objects.filter(
            medidores_asociados__porcion__isnull=False
        ).distinct()
        
        # Get equipment with pilots (critical monitoring points)
        equipment_with_pilots = Equipo.objects.exclude(
            piloto__isnull=True
        ).exclude(piloto='')
        
        # Combine both sets
        critical_equipment = (equipment_with_billing | equipment_with_pilots).distinct()
        
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
        critical = AlertService.get_critical_equipment()
        offline = AlertService.get_offline_equipment()
        
        return critical & offline
    
    @staticmethod
    def send_equipment_alert(equipment_list):
        """
        Send email alert for offline equipment.
        
        Args:
            equipment_list: List or QuerySet of Equipo objects
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not equipment_list:
            logger.info("No equipment to alert about")
            return False
        
        # Prepare equipment data
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
            'alert_sent': False,
        }
        
        if equipment_list:
            result['alert_sent'] = AlertService.send_equipment_alert(equipment_list)
            result['equipment_ids'] = [e.id_equipo for e in equipment_list]
        
        logger.info(f"Alert check completed: {result}")
        return result
