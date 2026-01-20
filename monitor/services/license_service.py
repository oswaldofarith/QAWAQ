import jwt
import datetime
import os
from django.conf import settings
from django.utils import timezone
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

@dataclass
class LicenseInfo:
    client_name: str
    expiration_date: datetime.date
    is_valid: bool
    status_message: str
    days_remaining: int

class LicenseService:
    # Use a separate secret for licensing if possible, otherwise fallback to SECRET_KEY
    # In production, this should be provided securely and NOT hardcoded.
    LICENSE_SECRET = os.environ.get('QAWAQ_LICENSE_SECRET', settings.SECRET_KEY)
    ALGORITHM = "HS256"
    LICENSE_FILE_PATH = os.path.join(settings.BASE_DIR, 'qawaq.license')

    @classmethod
    def generate_license(cls, client_name: str, days_valid: int) -> str:
        """
        Generate a signed license key string.
        """
        expiration = timezone.now().date() + datetime.timedelta(days=days_valid)
        
        payload = {
            'client': client_name,
            'exp_date': expiration.isoformat(),
            'generated_at': timezone.now().isoformat(),
        }
        
        token = jwt.encode(payload, cls.LICENSE_SECRET, algorithm=cls.ALGORITHM)
        return token

    @classmethod
    def load_license_file(cls) -> Optional[str]:
        """Read the license token from file system."""
        if not os.path.exists(cls.LICENSE_FILE_PATH):
            return None
        
        try:
            with open(cls.LICENSE_FILE_PATH, 'r') as f:
                return f.read().strip()
        except Exception:
            return None

    @classmethod
    def save_license_file(cls, token: str) -> None:
        """Save the license token to file system."""
        with open(cls.LICENSE_FILE_PATH, 'w') as f:
            f.write(token.strip())

    @classmethod
    def validate_license(cls) -> LicenseInfo:
        """
        Check license status.
        Returns LicenseInfo object with details.
        """
        token = cls.load_license_file()
        
        if not token:
            return LicenseInfo(
                client_name="Unknown",
                expiration_date=datetime.date.min,
                is_valid=False,
                status_message="No license found. Please contact support.",
                days_remaining=0
            )

        try:
            # Decode payload (verify signature)
            payload = jwt.decode(token, cls.LICENSE_SECRET, algorithms=[cls.ALGORITHM])
            
            client_name = payload.get('client', 'Unknown')
            exp_date_str = payload.get('exp_date')
            expiration_date = datetime.date.fromisoformat(exp_date_str)
            today = timezone.now().date()
            
            days_remaining = (expiration_date - today).days
            
            if days_remaining < 0:
                return LicenseInfo(
                    client_name=client_name,
                    expiration_date=expiration_date,
                    is_valid=False,
                    status_message=f"License expired on {expiration_date}. Please renew.",
                    days_remaining=days_remaining
                )
            
            return LicenseInfo(
                client_name=client_name,
                expiration_date=expiration_date,
                is_valid=True,
                status_message="Active",
                days_remaining=days_remaining
            )

        except jwt.ExpiredSignatureError:
            # Should be caught by logic above if exp claim used, but we used custom claim
            return LicenseInfo(
                client_name="Unknown",
                expiration_date=datetime.date.min,
                is_valid=False,
                status_message="License expired (Signature verification).",
                days_remaining=0
            )
        except jwt.InvalidTokenError:
            return LicenseInfo(
                client_name="Unknown",
                expiration_date=datetime.date.min,
                is_valid=False,
                status_message="Invalid license key.",
                days_remaining=0
            )
        except Exception as e:
            return LicenseInfo(
                client_name="Unknown",
                expiration_date=datetime.date.min,
                is_valid=False,
                status_message=f"License error: {str(e)}",
                days_remaining=0
            )
