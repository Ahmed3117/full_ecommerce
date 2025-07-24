from django.core.management.base import BaseCommand
from services.fawaterak_service import fawaterak_service
from products.models import Pill
import json

class Command(BaseCommand):
    help = 'Test Fawaterak integration with real API'

    def add_arguments(self, parser):
        parser.add_argument('--pill-id', type=int, help='Test with specific pill ID', default=30)
        parser.add_argument('--test-webhook', action='store_true', help='Test webhook processing')

    def handle(self, *args, **options):
        self.stdout.write('=== Testing Fawaterak Real API Integration ===')
        
        pill_id = options['pill_id']
        
        try:
            pill = Pill.objects.get(id=pill_id)
            self.stdout.write(f'Testing with Pill ID: {pill_id}')
            self.stdout.write(f'Pill Number: {pill.pill_number}')
            self.stdout.write(f'Customer: {pill.pilladdress.name if hasattr(pill, "pilladdress") else "No address"}')
            self.stdout.write(f'Total Amount: {pill.final_price()} EGP')
            self.stdout.write(f'Items Count: {pill.items.count()}')
            
            if options['test_webhook']:
                # Test webhook with successful payment
                webhook_data = {
                    'status': 'paid',
                    'invoiceId': 'TEST-12345',
                    'payLoad': {
                        'pill_number': pill.pill_number,
                        'pill_id': pill.id,
                        'user_id': pill.user.id
                    },
                    'created_at': '2025-01-24T01:26:54Z'
                }
                
                self.stdout.write('\n=== Testing Webhook Processing ===')
                result = fawaterak_service.process_webhook_payment(webhook_data)
                
                if result['success']:
                    self.stdout.write(self.style.SUCCESS('✓ Webhook test successful!'))
                    self.stdout.write(f'Result: {json.dumps(result, indent=2)}')
                    
                    # Check if pill was updated
                    pill.refresh_from_db()
                    self.stdout.write(f'Pill paid status updated: {pill.paid}')
                else:
                    self.stdout.write(self.style.ERROR(f'✗ Webhook test failed: {result["error"]}'))
            else:
                # Test real API payment creation
                self.stdout.write('\n=== Creating Real Payment Invoice ===')
                result = fawaterak_service.create_payment_invoice(pill)
                
                if result['success']:
                    self.stdout.write(self.style.SUCCESS('✓ Payment invoice created successfully!'))
                    self.stdout.write(f'Payment URL: {result["data"]["payment_url"]}')
                    self.stdout.write(f'Invoice ID: {result["data"]["invoice_id"]}')
                    self.stdout.write(f'Invoice Key: {result["data"]["invoice_key"]}')
                    self.stdout.write(f'Total Amount: {result["data"]["total_amount"]} EGP')
                    
                    # Test URLs for Postman
                    self.stdout.write('\n=== Postman Test Instructions ===')
                    self.stdout.write('1. Copy the Payment URL above and open it in browser')
                    self.stdout.write('2. Use these test cards:')
                    self.stdout.write('   SUCCESS: 5123450000000008, 12/26, CVV: 100')
                    self.stdout.write('   SUCCESS: 4005 5500 0000 0001, 12/26, CVV: 100')
                    self.stdout.write('   FAIL: 5543474002249996, 05/21, CVV: 123')
                    self.stdout.write('3. Test API endpoints:')
                    self.stdout.write(f'   POST http://127.0.0.1:8000/api/payment/create/{pill_id}/')
                    self.stdout.write(f'   GET http://127.0.0.1:8000/api/payment/status/{pill_id}/')
                    
                else:
                    self.stdout.write(self.style.ERROR(f'✗ Failed: {result["error"]}'))
                    
        except Pill.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ Pill {pill_id} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))