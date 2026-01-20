import os
import django

# Setup Django FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qawaq_project.settings')
django.setup()

# THEN import services
from monitor.services.license_service import LicenseService

def bootstrap():
    print("Bootstrapping license...")
    try:
        token = LicenseService.generate_license("QAWAQ Trial", 30, email="soporte@qawaq.com")
        LicenseService.save_license_file(token)
        print(f"License saved to {LicenseService.LICENSE_FILE_PATH}")
        
        info = LicenseService.validate_license()
        print(f"Validation: {info.is_valid}, {info.status_message}")
        print("SUCCESS")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    bootstrap()
