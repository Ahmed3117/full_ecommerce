from django.core.management.base import BaseCommand
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Debug Fawaterak configuration'

    def handle(self, *args, **options):
        self.stdout.write('=== Fawaterak Configuration Debug ===')
        
        # Check environment variables
        self.stdout.write('\n1. Environment Variables:')
        env_vars = [
            'FAWATERAK_API_KEY',
            'FAWATERAK_PROVIDER_KEY', 
            'FAWATERAK_BASE_URL',
            'FAWATERAK_WEBHOOK_URL',
            'SITE_URL'
        ]
        
        for var in env_vars:
            value = os.getenv(var)
            if value:
                if 'KEY' in var or 'TOKEN' in var:
                    # Hide sensitive data
                    display_value = f"{value[:20]}..." if len(value) > 20 else value
                else:
                    display_value = value
                self.stdout.write(f"  {var}: {display_value}")
            else:
                self.stdout.write(self.style.ERROR(f"  {var}: NOT SET"))
        
        # Check Django settings
        self.stdout.write('\n2. Django Settings:')
        try:
            api_key = settings.FAWATERAK_API_KEY
            self.stdout.write(f"  FAWATERAK_API_KEY: {api_key[:20]}..." if api_key else "NOT SET")
        except AttributeError:
            self.stdout.write(self.style.ERROR("  FAWATERAK_API_KEY: NOT CONFIGURED"))
        
        try:
            base_url = settings.FAWATERAK_BASE_URL
            self.stdout.write(f"  FAWATERAK_BASE_URL: {base_url}")
        except AttributeError:
            self.stdout.write(self.style.ERROR("  FAWATERAK_BASE_URL: NOT CONFIGURED"))
        
        try:
            site_url = settings.SITE_URL
            self.stdout.write(f"  SITE_URL: {site_url}")
        except AttributeError:
            self.stdout.write(self.style.ERROR("  SITE_URL: NOT CONFIGURED"))
        
        # Test manual API call
        self.stdout.write('\n3. Testing Manual API Call:')
        
        try:
            import requests
            
            headers = {
                'auth': f'Bearer {settings.FAWATERAK_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            self.stdout.write(f"  Headers: {headers}")
            
            # Simple test payload
            test_payload = {
                "cartTotal": "100",
                "currency": "EGP",
                "customer": {
                    "first_name": "Test",
                    "last_name": "User",
                    "email": "test@test.com"
                },
                "cartItems": [
                    {
                        "name": "Test Product",
                        "price": "100",
                        "quantity": "1"
                    }
                ]
            }
            
            response = requests.post(
                'https://app.fawaterk.com/api/v2/createInvoiceLink',
                json=test_payload,
                headers=headers,
                timeout=10
            )
            
            self.stdout.write(f"  Response Status: {response.status_code}")
            self.stdout.write(f"  Response: {response.text}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Manual API test failed: {e}"))