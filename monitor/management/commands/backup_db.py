"""
Django management command for backing up PostgreSQL database.

Usage:
    python manage.py backup_db
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import os
import gzip
import shutil


class Command(BaseCommand):
    help = 'Backup PostgreSQL database with automatic rotation (keeps last 30 days)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-days',
            type=int,
            default=30,
            help='Number of days to keep backups (default: 30)'
        )

    def handle(self, *args, **options):
        keep_days = options['keep_days']
        
        # Backup directory
        backup_dir = Path(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        # Database configuration
        db_config = settings.DATABASES['default']
        db_name = db_config['NAME']
        db_user = db_config['USER']
        db_password = db_config['PASSWORD']
        db_host = db_config['HOST']
        db_port = db_config['PORT']
        
        # Backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'backup_{timestamp}.sql'
        compressed_file = backup_dir / f'backup_{timestamp}.sql.gz'
        
        self.stdout.write(self.style.SUCCESS(f'Starting database backup...'))
        
        try:
            # Set password environment variable for pg_dump
            env = os.environ.copy()
            env['PGPASSWORD'] = db_password
            
            # Run pg_dump
            self.stdout.write(f'Dumping database: {db_name}')
            with open(backup_file, 'w') as f:
                subprocess.run([
                    'pg_dump',
                    '-h', db_host,
                    '-p', db_port,
                    '-U', db_user,
                    '-d', db_name,
                    '--no-owner',
                    '--no-acl',
                ], stdout=f, env=env, check=True)
            
            # Compress the backup
            self.stdout.write('Compressing backup...')
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed file
            backup_file.unlink()
            
            # Get backup size
            size_mb = compressed_file.stat().st_size / (1024 * 1024)
            
            self.stdout.write(self.style.SUCCESS(
                f'✓ Backup completed successfully: {compressed_file.name} ({size_mb:.2f} MB)'
            ))
            
            # Clean up old backups
            self.cleanup_old_backups(backup_dir, keep_days)
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f'✗ Backup failed: {e}'))
            if backup_file.exists():
                backup_file.unlink()
            raise
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Unexpected error: {e}'))
            raise

    def cleanup_old_backups(self, backup_dir, keep_days):
        """Remove backups older than keep_days."""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        removed_count = 0
        
        for backup_file in backup_dir.glob('backup_*.sql.gz'):
            # Extract date from filename (backup_YYYYMMDD_HHMMSS.sql.gz)
            try:
                date_str = backup_file.stem.split('_')[1]  # Get YYYYMMDD part
                backup_date = datetime.strptime(date_str, '%Y%m%d')
                
                if backup_date < cutoff_date:
                    backup_file.unlink()
                    removed_count += 1
                    self.stdout.write(f'Removed old backup: {backup_file.name}')
            except (IndexError, ValueError):
                # Skip files that don't match expected format
                continue
        
        if removed_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f'✓ Cleaned up {removed_count} old backup(s)'
            ))
        else:
            self.stdout.write('No old backups to clean up')
