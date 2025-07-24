from django.core.management.base import BaseCommand
from django.conf import settings
from services.khazenly_service import khazenly_service

class Command(BaseCommand):
    help = 'Test Khazenly connection using refresh token'

    def handle(self, *args, **options):
        self.stdout.write('=== Testing Khazenly Connection ===')
        self.stdout.write(f'Base URL: {settings.KHAZENLY_BASE_URL}')
        self.stdout.write(f'Store Name: {settings.KHAZENLY_STORE_NAME}')
        self.stdout.write(f'Has Refresh Token: {"Yes" if settings.KHAZENLY_REFRESH_TOKEN else "No"}')
        
        if not settings.KHAZENLY_REFRESH_TOKEN:
            self.stdout.write(self.style.ERROR('✗ No refresh token in settings'))
            self.stdout.write('Please add KHAZENLY_REFRESH_TOKEN to your .env file')
            return
        
        token = khazenly_service.get_access_token()
        if token:
            self.stdout.write(self.style.SUCCESS('✓ Khazenly connection successful!'))
            self.stdout.write(f'Access token: {token[:20]}...')
        else:
            self.stdout.write(self.style.ERROR('✗ Khazenly connection failed!'))