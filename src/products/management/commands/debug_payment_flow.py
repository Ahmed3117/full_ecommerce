from django.core.management.base import BaseCommand
from services.fawaterak_service import fawaterak_service
from products.models import Pill
import json

class Command(BaseCommand):
    help = 'Debug the complete payment flow'

    def handle(self, *args, **options):
        self.stdout.write('=== Debugging Payment Flow ===')
        
        try:
            pill = Pill.objects.get(id=30)
            self.stdout.write(f'Testing with Pill: {pill.pill_number}')
            
            # Test 1: Create payment invoice with debug info
            self.stdout.write('\n1. Creating payment invoice...')
            result = fawaterak_service.create_payment_invoice(pill)
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS('✓ Payment invoice created'))
                self.stdout.write(f'Payment URL: {result["data"]["payment_url"]}')
                self.stdout.write(f'Invoice ID: {result["data"]["invoice_id"]}')
                
                # Test 2: Check what happens when we manually call success/failed
                self.stdout.write('\n2. Testing redirect URLs manually...')
                
                # Import requests for manual testing
                import requests
                
                # Test success URL
                success_url = f'http://127.0.0.1:8000/api/payment/success/{pill.pill_number}/'
                self.stdout.write(f'Testing: {success_url}')
                
                try:
                    response = requests.get(success_url, timeout=10)
                    self.stdout.write(f'Success URL response: {response.status_code}')
                    self.stdout.write(f'Response: {response.text[:200]}...')
                except Exception as e:
                    self.stdout.write(f'Success URL error: {e}')
                
                # Test failed URL  
                failed_url = f'http://127.0.0.1:8000/api/payment/failed/{pill.pill_number}/'
                self.stdout.write(f'Testing: {failed_url}')
                
                try:
                    response = requests.get(failed_url, timeout=10)
                    self.stdout.write(f'Failed URL response: {response.status_code}')
                    self.stdout.write(f'Response: {response.text[:200]}...')
                except Exception as e:
                    self.stdout.write(f'Failed URL error: {e}')
                
                # Test 3: Manual webhook simulation
                self.stdout.write('\n3. Testing webhook simulation...')
                webhook_data = {
                    'status': 'paid',
                    'invoiceId': result["data"]["invoice_id"],
                    'payLoad': {
                        'pill_number': pill.pill_number,
                        'pill_id': pill.id,
                        'user_id': pill.user.id
                    }
                }
                
                webhook_result = fawaterak_service.process_webhook_payment(webhook_data)
                if webhook_result['success']:
                    self.stdout.write(self.style.SUCCESS('✓ Webhook simulation successful'))
                    
                    # Check pill status
                    pill.refresh_from_db()
                    self.stdout.write(f'Pill paid status: {pill.paid}')
                else:
                    self.stdout.write(self.style.ERROR(f'✗ Webhook failed: {webhook_result["error"]}'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ Failed to create invoice: {result["error"]}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {e}'))