"""
Telegram notification service for critical equipment alerts.

Sends formatted notifications to Telegram when critical equipment goes offline.
Uses requests library directly with Telegram Bot API for maximum compatibility.
"""
import logging
import requests
from django.conf import settings
from django.utils import timezone
from monitor.models import UserProfile

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """Service for sending Telegram notifications about critical equipment failures."""
    
    def __init__(self):
        """Initialize the Telegram bot."""
        self.bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        self.enabled = getattr(settings, 'TELEGRAM_ENABLED', False) and bool(self.bot_token)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def verify_bot_connection(self):
        """
        Verify that the bot is properly configured and can connect to Telegram.
        
        Returns:
            dict: Status information about the bot connection
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'Telegram bot is not enabled or token is missing'
            }
        
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('ok'):
                bot_info = data['result']
                return {
                    'success': True,
                    'bot_username': bot_info.get('username'),
                    'bot_id': bot_info.get('id'),
                    'bot_name': bot_info.get('first_name')
                }
            else:
                return {
                    'success': False,
                    'error': data.get('description', 'Unknown error')
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram connection verification failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def format_equipment_message(self, equipment_data):
        """
        Format equipment failure data into a Telegram message.
        
        Args:
            equipment_data: List of dictionaries containing equipment information
        
        Returns:
            str: Formatted message for Telegram
        """
        message_lines = [
            "🚨 <b>ALERTA: Equipos Críticos OFFLINE</b>",
            "",
            f"Se detectaron {len(equipment_data)} equipos críticos fuera de línea:",
            ""
        ]
        
        for idx, item in enumerate(equipment_data, 1):
            equipo = item['equipo']
            message_lines.extend([
                f"<b>{idx}. {equipo.id_equipo}</b>",
                f"   📍 IP: <code>{equipo.ip}</code>",
                f"   ⏱️ Tiempo offline: {item['downtime']}",
                f"   📊 Medidores afectados: {item['medidor_count']}",
                f"   🏘️ Porciones: {item['affected_portions']}",
                ""
            ])
        
        message_lines.extend([
            f"📅 Fecha de alerta: {timezone.now().strftime('%d/%m/%Y %H:%M')}",
            "",
            "⚠️ Se requiere atención inmediata"
        ])
        
        return "\n".join(message_lines)
    
    def send_message(self, chat_id, text, parse_mode='HTML'):
        """
        Send a message to a Telegram chat.
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: Parse mode (HTML or Markdown)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return data.get('ok', False)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
            return False
    
    def send_critical_alert(self, equipment_data, recipients=None):
        """
        Send critical equipment alert to Telegram.
        
        Args:
            equipment_data: List of dictionaries containing equipment information
            recipients: List of chat IDs to send to. If None, sends to all users with telegram_notifications enabled
        
        Returns:
            dict: Summary of send results
        """
        if not self.enabled:
            logger.warning("Telegram notifications are disabled")
            return {
                'success': False,
                'sent_count': 0,
                'failed_count': 0,
                'error': 'Telegram is not enabled'
            }
        
        if not equipment_data:
            logger.info("No equipment data to send")
            return {
                'success': True,
                'sent_count': 0,
                'failed_count': 0
            }
        
        # Get recipients if not provided
        if recipients is None:
            recipients = []
            profiles = UserProfile.objects.filter(
                telegram_notifications=True,
                telegram_chat_id__isnull=False
            ).exclude(telegram_chat_id='')
            
            for profile in profiles:
                recipients.append(profile.telegram_chat_id)
        
        if not recipients:
            logger.info("No Telegram recipients configured")
            return {
                'success': True,
                'sent_count': 0,
                'failed_count': 0,
                'error': 'No recipients configured'
            }
        
        # Format message
        message = self.format_equipment_message(equipment_data)
        
        # Send to each recipient
        sent_count = 0
        failed_count = 0
        errors = []
        
        for chat_id in recipients:
            if self.send_message(chat_id, message):
                sent_count += 1
                logger.info(f"Telegram alert sent to {chat_id}")
            else:
                failed_count += 1
                error_msg = f"Failed to send to {chat_id}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        result = {
            'success': sent_count > 0,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_recipients': len(recipients)
        }
        
        if errors:
            result['errors'] = errors
        
        return result
    
    def send_test_message(self, chat_id):
        """
        Send a test message to verify the configuration.
        
        Args:
            chat_id: Telegram chat ID to send test message to
        
        Returns:
            dict: Result of the test
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'Telegram is not enabled'
            }
        
        test_message = (
            "✅ <b>Test de Notificación QAWAQ</b>\n\n"
            "Este es un mensaje de prueba del sistema de monitoreo.\n\n"
            f"📅 {timezone.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            "Si recibes este mensaje, las notificaciones están configuradas correctamente."
        )
        
        if self.send_message(chat_id, test_message):
            return {
                'success': True,
                'message': 'Test message sent successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to send test message'
            }
