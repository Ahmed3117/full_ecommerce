from django.core.management.base import BaseCommand
from services.fawaterak_service import fawaterak_service
from products.models import Pill

class Command(BaseCommand):
    help = 'Test complete payment flow'

    def handle(self, *args, **options):
        self.stdout.write('=== Testing Complete Payment Flow ===')
        
        try:
            # Reset pill payment status
            pill = Pill.objects.get(id=30)
            pill.paid = False
            pill.save()
            self.stdout.write(f'Reset pill payment status: {pill.paid}')
            
            # Create payment invoice
            self.stdout.write('\n1. Creating payment invoice...')
            result = fawaterak_service.create_payment_invoice(pill)
            
            if result['success']:
                payment_url = result['data']['payment_url']
                invoice_id = result['data']['invoice_id']
                
                self.stdout.write(self.style.SUCCESS('✓ Payment invoice created'))
                self.stdout.write(f'Payment URL: {payment_url}')
                self.stdout.write(f'Invoice ID: {invoice_id}')
                
                # Simulate successful payment
                self.stdout.write('\n2. Simulating successful payment...')
                webhook_data = {
                    'status': 'paid',
                    'invoiceId': invoice_id,
                    'payLoad': {
                        'pill_number': pill.pill_number,
                        'pill_id': pill.id,
                        'user_id': pill.user.id
                    }
                }
                
                webhook_result = fawaterak_service.process_webhook_payment(webhook_data)
                if webhook_result['success']:
                    self.stdout.write(self.style.SUCCESS('✓ Webhook processed'))
                    
                    # Check final status
                    pill.refresh_from_db()
                    self.stdout.write(f'Final pill status: {"PAID" if pill.paid else "UNPAID"}')
                    
                    if pill.paid:
                        self.stdout.write(self.style.SUCCESS('🎉 COMPLETE FLOW SUCCESSFUL!'))
                        self.stdout.write(f'\nNow test manually:')
                        self.stdout.write(f'1. Open: {payment_url}')
                        self.stdout.write(f'2. Use card: 5123450000000008, 12/26, 100, "Fawaterak test"')
                        self.stdout.write(f'3. Complete payment')
                        self.stdout.write(f'4. Should redirect to success page')
                    else:
                        self.stdout.write(self.style.ERROR('❌ Pill not marked as paid'))
                else:
                    self.stdout.write(self.style.ERROR(f'✗ Webhook failed: {webhook_result["error"]}'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ Invoice creation failed: {result["error"]}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {e}'))