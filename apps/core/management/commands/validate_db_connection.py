from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = 'Validates database connection'

    def handle(self, *args, **options):
        self.stdout.write('Testing database connection...')
        
        conn = connections['default']
        try:
            conn.ensure_connection()
            self.stdout.write(self.style.SUCCESS('Database connection successful!'))
            self.stdout.write(f"Using engine: {conn.settings_dict['ENGINE']}")
            self.stdout.write(f"Database name: {conn.settings_dict.get('NAME', 'unknown')}")
            self.stdout.write(f"Database host: {conn.settings_dict.get('HOST', 'unknown')}")
        except OperationalError as e:
            self.stdout.write(self.style.ERROR(f'Database connection failed! Error: {e}')) 