"""
Django management command to test Telegram bot configuration.

Usage:
    python manage.py test_telegram <chat_id>
    python manage.py test_telegram --check
"""
from django.core.management.base import BaseCommand
from monitor.services.telegram_service import TelegramNotificationService


class Command(BaseCommand):
    help = 'Test Telegram bot configuration and send test messages'

    def add_arguments(self, parser):
        parser.add_argument(
            'chat_id',
            nargs='?',
            type=str,
            help='Telegram chat ID to send test message to'
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Only check bot connection without sending message'
        )

    def handle(self, *args, **options):
        telegram_service = TelegramNotificationService()
        
        self.stdout.write('Testing Telegram configuration...\n')
        
        # Check if Telegram is enabled
        if not telegram_service.enabled:
            self.stdout.write(
                self.style.ERROR('✗ Telegram is not enabled or bot token is missing')
            )
            self.stdout.write('\nPlease configure TELEGRAM_BOT_TOKEN in your .env file')
            return
        
        # Verify bot connection
        self.stdout.write('Verifying bot connection...')
        connection_result = telegram_service.verify_bot_connection()
        
        if connection_result['success']:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Bot connected successfully!")
            )
            self.stdout.write(f"  Bot Username: @{connection_result['bot_username']}")
            self.stdout.write(f"  Bot Name: {connection_result['bot_name']}")
            self.stdout.write(f"  Bot ID: {connection_result['bot_id']}")
        else:
            self.stdout.write(
                self.style.ERROR(f"✗ Bot connection failed: {connection_result.get('error')}")
            )
            return
        
        # If only checking connection, stop here
        if options['check']:
            self.stdout.write('\n' + self.style.SUCCESS('Connection check complete!'))
            return
        
        # Send test message if chat_id provided
        chat_id = options.get('chat_id')
        if not chat_id:
            self.stdout.write('\n' + self.style.WARNING('No chat ID provided. Use --check to only verify connection.'))
            self.stdout.write('\nUsage: python manage.py test_telegram <chat_id>')
            self.stdout.write('Get your chat ID by messaging @userinfobot on Telegram')
            return
        
        self.stdout.write(f'\nSending test message to chat ID: {chat_id}...')
        test_result = telegram_service.send_test_message(chat_id)
        
        if test_result['success']:
            self.stdout.write(
                self.style.SUCCESS('✓ Test message sent successfully!')
            )
            self.stdout.write('\nCheck your Telegram to confirm receipt.')
        else:
            self.stdout.write(
                self.style.ERROR(f"✗ Failed to send test message: {test_result.get('error')}")
            )
            self.stdout.write('\nPossible reasons:')
            self.stdout.write('  - Invalid chat ID')
            self.stdout.write('  - User has not started a conversation with the bot')
            self.stdout.write('  - Bot was blocked by the user')
