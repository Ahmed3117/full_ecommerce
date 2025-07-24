from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import json

class Command(BaseCommand):
    help = 'Test Fawaterak login and get fresh token'

    def handle(self, *args, **options):
        self.stdout.write('=== Testing Fawaterak Login ===')
        
        # Try to login with username/password to get a fresh token
        login_data = {
            'email': settings.FAWATERAK_USERNAME,
            'password': settings.FAWATERAK_PASSWORD
        }
        
        login_endpoints = [
            'https://app.fawaterk.com/api/login',
            'https://staging.fawaterk.com/api/login',
            'https://app.fawaterk.com/api/v2/login',
            'https://staging.fawaterk.com/api/v2/login'
        ]
        
        for endpoint in login_endpoints:
            self.stdout.write(f'\nTrying login at: {endpoint}')
            try:
                response = requests.post(endpoint, json=login_data, timeout=10)
                self.stdout.write(f'Status: {response.status_code}')
                self.stdout.write(f'Response: {response.text}')
                
                if response.status_code == 200:
                    data = response.json()
                    if 'token' in data or 'access_token' in data:
                        token = data.get('token') or data.get('access_token')
                        self.stdout.write(self.style.SUCCESS(f'✓ New token obtained: {token[:20]}...'))
                        
                        # Test the new token
                        self._test_token(token)
                        
            except Exception as e:
                self.stdout.write(f'Error: {str(e)}')
    
    def _test_token(self, token):
        """Test the obtained token"""
        self.stdout.write(f'\n=== Testing New Token ===')
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
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
        
        test_urls = [
            'https://app.fawaterk.com/api/v2/createInvoiceLink',
            'https://staging.fawaterk.com/api/v2/createInvoiceLink'
        ]
        
        for url in test_urls:
            try:
                response = requests.post(url, json=test_payload, headers=headers, timeout=10)
                self.stdout.write(f'{url}: {response.status_code} - {response.text[:200]}...')
                
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS(f'✓ Token works with {url}'))
                    self.stdout.write(f'Update your .env with: FAWATERAK_API_KEY={token}')
                    
            except Exception as e:
                self.stdout.write(f'Error testing {url}: {str(e)}')