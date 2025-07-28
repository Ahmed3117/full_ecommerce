from django.core.management.base import BaseCommand
import requests
import json

class Command(BaseCommand):
    help = 'Test Khazenly webhook endpoint with different scenarios'

    def add_arguments(self, parser):
        parser.add_argument('--url', type=str, help='Webhook URL to test', default='http://localhost:8000/api/webhook/khazenly/order-status/')
        parser.add_argument('--status', type=str, help='Khazenly status to test', default='Out for Delivery')
        parser.add_argument('--order-ref', type=str, help='Order reference', default='KH-BOOKIFAY-01682390')
        parser.add_argument('--merchant-ref', type=str, help='Merchant reference', default='92669214257708369311-1753673013')
        parser.add_argument('--test-all', action='store_true', help='Test all status scenarios')

    def handle(self, *args, **options):
        url = options['url']
        
        if options['test_all']:
            self.test_all_scenarios(url)
        else:
            self.test_single_webhook(url, options['status'], options['order_ref'], options['merchant_ref'])

    def test_single_webhook(self, url, status, order_ref, merchant_ref):
        payload = {
            "store": "https://bookefay.com",
            "status": status,
            "requestMethod": "POST",
            "orderSupplierId": order_ref,
            "orderReference": order_ref,
            "merchantReference": merchant_ref,
            "orderType": "New Order",
            "credentials": "BOOKIFAY",
            "callbackUrl": url
        }
        
        self.stdout.write(f"=== Testing Khazenly Webhook: {status} ===")
        self.stdout.write(f"URL: {url}")
        self.stdout.write(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            self.stdout.write(f"Response Status: {response.status_code}")
            self.stdout.write(f"Response Body: {response.text}")
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("✓ Webhook test successful!"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ Webhook test failed with status {response.status_code}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error testing webhook: {str(e)}"))

    def test_all_scenarios(self, url):
        scenarios = [
            ("Out for Delivery", "Should update pill to 'Under Delivery'"),
            ("Order Delivered", "Should update pill to 'Delivered'"),
            ("Order Delivery Failed", "Should update pill to 'Refused'"),
            ("Cancelled", "Should update pill to 'Canceled'"),
            ("Order Ready", "Should not change pill status"),
        ]
        
        self.stdout.write("=== Testing All Webhook Scenarios ===")
        
        for status, expected in scenarios:
            self.stdout.write(f"\n--- Testing: {status} ---")
            self.stdout.write(f"Expected: {expected}")
            self.test_single_webhook(
                url, 
                status, 
                "KH-BOOKIFAY-01682390", 
                "92669214257708369311-1753673013"
            )