"""
Management command to test email notification configuration.
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test email notification configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            nargs='?',
            type=str,
            help='Email address to send test to (optional, defaults to ADMINS)'
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Only check email configuration without sending'
        )

    def handle(self, *args, **options):
        self.stdout.write("DEBUG: Settings loaded successfully")
        self.stdout.write("\nTesting email configuration...\n")
        
        # Check configuration
        if options['check']:
            self.check_configuration()
            return
        
        # Determine recipients
        recipient = options.get('recipient')
        if recipient:
            recipients = [recipient]
            self.stdout.write(f"Sending test email to: {recipient}")
        else:
            if not settings.ADMINS:
                self.stdout.write(self.style.ERROR(
                    "✗ No ADMINS configured in settings.py"
                ))
                return
            recipients = [admin[1] for admin in settings.ADMINS]
            self.stdout.write(f"Sending test email to ADMINS: {', '.join(recipients)}")
        
        # Send test email
        try:
            subject = f"🧪 QAWAQ Email Test - {timezone.now().strftime('%d/%m/%Y %H:%M')}"
            
            message = f"""
¡Hola!

Este es un mensaje de prueba del sistema de notificaciones de QAWAQ.

Si estás recibiendo este correo, significa que:
✓ La configuración de correo está funcionando correctamente
✓ El servidor SMTP está accesible
✓ Las credenciales son válidas

Detalles de la prueba:
- Fecha: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}
- Servidor: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}
- Usuario: {settings.EMAIL_HOST_USER}
- TLS: {'Activado' if settings.EMAIL_USE_TLS else 'Desactivado'}

Este correo fue enviado automáticamente por el comando:
python manage.py test_email

---
Sistema de Monitoreo QAWAQ
            """
            
            html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .success {{ color: #28a745; font-weight: bold; }}
        .info-box {{ background: white; padding: 15px; margin: 15px 0; 
                     border-left: 4px solid #667eea; border-radius: 4px; }}
        .footer {{ text-align: center; color: #666; margin-top: 30px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 QAWAQ Email Test</h1>
        </div>
        <div class="content">
            <p>¡Hola!</p>
            
            <p>Este es un mensaje de prueba del sistema de notificaciones de QAWAQ.</p>
            
            <div class="info-box">
                <p class="success">✓ La configuración de correo está funcionando correctamente</p>
                <p class="success">✓ El servidor SMTP está accesible</p>
                <p class="success">✓ Las credenciales son válidas</p>
            </div>
            
            <h3>Detalles de la prueba:</h3>
            <ul>
                <li><strong>Fecha:</strong> {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}</li>
                <li><strong>Servidor:</strong> {settings.EMAIL_HOST}:{settings.EMAIL_PORT}</li>
                <li><strong>Usuario:</strong> {settings.EMAIL_HOST_USER}</li>
                <li><strong>TLS:</strong> {'Activado' if settings.EMAIL_USE_TLS else 'Desactivado'}</li>
            </ul>
            
            <p style="margin-top: 20px; font-size: 14px; color: #666;">
                Este correo fue enviado automáticamente por el comando:<br>
                <code style="background: #e9ecef; padding: 5px 10px; border-radius: 3px;">
                    python manage.py test_email
                </code>
            </p>
        </div>
        <div class="footer">
            <p>Sistema de Monitoreo QAWAQ</p>
        </div>
    </div>
</body>
</html>
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False,
                html_message=html_message,
            )
            
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Test email sent successfully to {len(recipients)} recipient(s)!"
            ))
            self.stdout.write("\nCheck your inbox for the test message.")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n✗ Failed to send test email: {e}"))
            self.stdout.write("\nPossible issues:")
            self.stdout.write("  - Invalid SMTP credentials")
            self.stdout.write("  - SMTP server unreachable")
            self.stdout.write("  - Firewall blocking connection")
            self.stdout.write("  - Invalid email configuration")
            logger.error(f"Email test failed: {e}")

    def check_configuration(self):
        """Check email configuration without sending."""
        self.stdout.write("Checking email configuration...\n")
        
        # Check ADMINS
        if settings.ADMINS:
            self.stdout.write(self.style.SUCCESS(
                f"✓ ADMINS configured: {len(settings.ADMINS)} recipient(s)"
            ))
            for name, email in settings.ADMINS:
                self.stdout.write(f"  - {name} <{email}>")
        else:
            self.stdout.write(self.style.WARNING("⚠ No ADMINS configured"))
        
        # Check EMAIL settings
        self.stdout.write(f"\n✓ Email Host: {settings.EMAIL_HOST}")
        self.stdout.write(f"✓ Email Port: {settings.EMAIL_PORT}")
        self.stdout.write(f"✓ Email User: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"✓ Use TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"✓ Default From: {settings.DEFAULT_FROM_EMAIL}")
        
        # Check password (without revealing it)
        if hasattr(settings, 'EMAIL_HOST_PASSWORD') and settings.EMAIL_HOST_PASSWORD:
            self.stdout.write(self.style.SUCCESS("✓ Email password is set"))
        else:
            self.stdout.write(self.style.WARNING("⚠ Email password not set"))
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write("Configuration check complete.")
        self.stdout.write("\nTo send a test email, run:")
        self.stdout.write(self.style.SUCCESS("  python manage.py test_email"))
        self.stdout.write("or")
        self.stdout.write(self.style.SUCCESS("  python manage.py test_email your-email@example.com"))
