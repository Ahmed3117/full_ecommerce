from django.core.management.base import BaseCommand
from django.conf import settings
from services.khazenly_service import khazenly_service
import requests

class Command(BaseCommand):
    help = 'Final test of Khazenly integration with correct credentials'

    def handle(self, *args, **options):
        self.stdout.write('=== Final Khazenly Integration Test ===')
        
        # Verify configuration
        self.stdout.write(f'Base URL: {settings.KHAZENLY_BASE_URL}')
        self.stdout.write(f'Client ID: {settings.KHAZENLY_CLIENT_ID[:20]}...')
        self.stdout.write(f'Store Name: {settings.KHAZENLY_STORE_NAME}')
        self.stdout.write(f'Has Refresh Token: {"Yes" if settings.KHAZENLY_REFRESH_TOKEN else "No"}')
        
        # Test token
        token = khazenly_service.get_access_token()
        if not token:
            self.stdout.write(self.style.ERROR('✗ Could not get access token'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'✓ Access token obtained: {token[:20]}...'))
        
        # Test minimal order creation
        test_payload = {
            "Order": {
                "orderId": "DJANGO-TEST-001",
                "totalAmount": 100.0,
                "invoiceTotalAmount": 100.0,
                "taxAmount": 0.0,
                "orderNumber": "DJANGO-TEST-001",
                "paymentMethod": "Cash-on-Delivery",
                "weight": 1.0,
                "storeCurrency": "EGP",
                "discountAmount": 0.0,
                "shippingFees": 0.0,
                "storeName": settings.KHAZENLY_STORE_NAME,
                "paymentStatus": "pending"
            },
            "Customer": {
                "Address1": "Test Address 123 Street",
                "City": "Cairo",
                "Country": "Egypt",
                "customerName": "Ahmed Test",
                "Tel": "01234567890"
            },
            "lineItems": [
                {
                    "SKU": "BOOKIFAY-TEST-001",
                    "Price": 100.0,
                    "ItemId": "1",
                    "ItemName": "Test Product",
                    "Quantity": 1,
                    "DiscountAmount": 0.0
                }
            ]
        }
        
        headers = {
            'auth': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{settings.KHAZENLY_BASE_URL}/services/apexrest/api/CreateOrder"
        
        self.stdout.write('\n=== Testing Order Creation ===')
        response = requests.post(url, json=test_payload, headers=headers, timeout=30)
        
        self.stdout.write(f'Status: {response.status_code}')
        self.stdout.write(f'Response: {response.text}')
        
        if response.status_code == 200:
            data = response.json()
            if data.get('resultCode') == 0:
                self.stdout.write(self.style.SUCCESS('✓ Test order created successfully!'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠ API returned: {data.get("result")}'))
        else:
            self.stdout.write(self.style.ERROR(f'✗ Request failed: {response.text}'))