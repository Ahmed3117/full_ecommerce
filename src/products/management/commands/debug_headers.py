from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import json

class Command(BaseCommand):
    help = 'Debug API headers and request'

    def handle(self, *args, **options):
        self.stdout.write('=== Debugging API Headers ===')
        
        api_key = settings.FAWATERAK_API_KEY
        self.stdout.write(f'API Key: {api_key}')
        self.stdout.write(f'API Key Length: {len(api_key) if api_key else 0}')
        self.stdout.write(f'API Key Type: {type(api_key)}')
        
        # Test different header formats
        header_formats = [
            {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},  # This is the correct one!
            {'auth': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            {'auth': f'Bearer {api_key.strip()}', 'Content-Type': 'application/json'},
            {'token': api_key, 'Content-Type': 'application/json'},
            {'Token': api_key, 'Content-Type': 'application/json'},
            {'X-API-Key': api_key, 'Content-Type': 'application/json'},
            {'X-Auth-Token': api_key, 'Content-Type': 'application/json'},
        ]
        
        test_payload = {
            "cartTotal": "100",
            "currency": "EGP",
            "customer": {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@test.com",
                "phone": "1234567890"
            },
            "cartItems": [
                {
                    "name": "Test Product",
                    "price": "100",
                    "quantity": "1"
                }
            ],
            "redirectionUrls": {
                "successUrl": "http://127.0.0.1:8000/success/",
                "failUrl": "http://127.0.0.1:8000/failed/",
                "pendingUrl": "http://127.0.0.1:8000/pending/"
            }
        }
        
        for i, headers in enumerate(header_formats, 1):
            self.stdout.write(f'\n--- Test {i}: {list(headers.keys())} ---')
            self.stdout.write(f'Headers: {headers}')
            
            try:
                response = requests.post(
                    'https://app.fawaterk.com/api/v2/createInvoiceLink',
                    json=test_payload,
                    headers=headers,
                    timeout=15
                )
                
                self.stdout.write(f'Status: {response.status_code}')
                self.stdout.write(f'Response: {response.text}')
                
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS(f'✓ SUCCESS with format {i}!'))
                    return
                elif response.status_code != 400 or 'Token Is Missing' not in response.text:
                    self.stdout.write(self.style.WARNING(f'⚠ Different error with format {i}'))
                    
            except Exception as e:
                self.stdout.write(f'Error: {e}')
        
        self.stdout.write(self.style.ERROR('\n✗ All header formats failed'))