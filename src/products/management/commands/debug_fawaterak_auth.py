from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import json

class Command(BaseCommand):
    help = 'Debug Fawaterak authentication and credentials'

    def handle(self, *args, **options):
        self.stdout.write('=== Fawaterak Authentication Debug ===')
        
        # Display current configuration
        self.stdout.write(f'API Key: {settings.FAWATERAK_API_KEY[:20]}...')
        self.stdout.write(f'Base URL: {settings.FAWATERAK_BASE_URL}')
        self.stdout.write(f'Provider Key: {settings.FAWATERAK_PROVIDER_KEY}')
        
        # Test different environments and endpoints
        environments = [
            {
                'name': 'Production',
                'base_url': 'https://app.fawaterk.com/api/v2',
                'create_url': 'https://app.fawaterk.com/api/v2/createInvoiceLink'
            },
            {
                'name': 'Staging',
                'base_url': 'https://staging.fawaterk.com/api/v2',
                'create_url': 'https://staging.fawaterk.com/api/v2/createInvoiceLink'
            }
        ]
        
        headers = {
            'auth': f'Bearer {settings.FAWATERAK_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Test minimal payload
        test_payload = {
            "cartTotal": "10",
            "currency": "EGP",
            "customer": {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@test.com"
            },
            "cartItems": [
                {
                    "name": "Test Product",
                    "price": "10",
                    "quantity": "1"
                }
            ]
        }
        
        for env in environments:
            self.stdout.write(f'\n=== Testing {env["name"]} Environment ===')
            self.stdout.write(f'URL: {env["create_url"]}')
            
            try:
                response = requests.post(
                    env['create_url'],
                    json=test_payload,
                    headers=headers,
                    timeout=10
                )
                
                self.stdout.write(f'Status Code: {response.status_code}')
                self.stdout.write(f'Response: {response.text[:500]}...')
                
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS(f'✓ {env["name"]} - SUCCESS!'))
                    data = response.json()
                    if data.get('status') == 'success':
                        payment_url = data.get('data', {}).get('url')
                        if payment_url:
                            self.stdout.write(f'Payment URL: {payment_url}')
                elif response.status_code == 401:
                    self.stdout.write(self.style.ERROR(f'✗ {env["name"]} - Authentication failed'))
                elif response.status_code == 400:
                    self.stdout.write(self.style.WARNING(f'⚠ {env["name"]} - Bad request (check payload)'))
                else:
                    self.stdout.write(self.style.ERROR(f'✗ {env["name"]} - HTTP {response.status_code}'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ {env["name"]} - Exception: {str(e)}'))
        
        # Test with alternative endpoint format
        self.stdout.write(f'\n=== Testing Alternative Endpoints ===')
        alt_endpoints = [
            'https://app.fawaterk.com/api/v2/invoiceInitPay',
            'https://staging.fawaterk.com/api/v2/invoiceInitPay',
            'https://app.fawaterk.com/api/v2/sendPayment',
            'https://staging.fawaterk.com/api/v2/sendPayment'
        ]
        
        for endpoint in alt_endpoints:
            self.stdout.write(f'\nTesting: {endpoint}')
            try:
                response = requests.post(endpoint, json=test_payload, headers=headers, timeout=10)
                self.stdout.write(f'Status: {response.status_code} - {response.text[:200]}...')
            except Exception as e:
                self.stdout.write(f'Error: {str(e)}')