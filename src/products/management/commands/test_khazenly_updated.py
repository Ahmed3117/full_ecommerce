from django.core.management.base import BaseCommand
from products.models import Pill
from services.khazenly_service import khazenly_service
import json

class Command(BaseCommand):
    help = 'Test Khazenly order creation with updated configuration'

    def add_arguments(self, parser):
        parser.add_argument('--pill-id', type=int, help='Pill ID to test', default=30)
        parser.add_argument('--test-token', action='store_true', help='Test access token refresh only')

    def handle(self, *args, **options):
        pill_id = options['pill_id']
        test_token_only = options['test_token']
        
        self.stdout.write('=== Khazenly Integration Test (Updated) ===')
        
        if test_token_only:
            self.stdout.write('Testing access token refresh...')
            
            # Test token refresh
            token = khazenly_service.get_access_token()
            
            if token:
                self.stdout.write(self.style.SUCCESS('✓ Access token obtained successfully'))
                self.stdout.write(f'Token (first 50 chars): {token[:50]}...')
            else:
                self.stdout.write(self.style.ERROR('✗ Failed to get access token'))
                self.stdout.write('Check your refresh token and credentials in .env')
            
            return
        
        # Test full order creation
        self.stdout.write(f'Testing order creation for Pill #{pill_id}...')
        
        try:
            pill = Pill.objects.get(id=pill_id)
            
            self.stdout.write(f'✓ Pill found: {pill.pill_number}')
            self.stdout.write(f'  - Total amount: {pill.final_price()} EGP')
            self.stdout.write(f'  - Items count: {pill.items.count()}')
            
            if hasattr(pill, 'pilladdress'):
                address = pill.pilladdress
                self.stdout.write(f'  - Customer: {address.name}')
                self.stdout.write(f'  - Address: {address.get_government_display()}')  # FIXED: Use correct field method
            else:
                self.stdout.write(self.style.ERROR('✗ No address information found'))
                return
            
            # Test order creation
            self.stdout.write('\n--- Testing Khazenly Order Creation ---')
            result = khazenly_service.create_order(pill)
            
            if result['success']:
                data = result['data']
                self.stdout.write(self.style.SUCCESS('✓ Khazenly order created successfully!'))
                self.stdout.write(f'  - Sales Order Number: {data.get("sales_order_number")}')
                self.stdout.write(f'  - Khazenly Order ID: {data.get("khazenly_order_id")}')
                self.stdout.write(f'  - Order Number: {data.get("order_number")}')
                
                # Show customer info
                customer = data.get('customer', {})
                if customer:
                    self.stdout.write(f'  - Customer ID: {customer.get("customerId")}')
                    self.stdout.write(f'  - Customer Name: {customer.get("customerName")}')
                
                # Show line items
                line_items = data.get('line_items', [])
                self.stdout.write(f'  - Line Items: {len(line_items)}')
                for item in line_items:
                    self.stdout.write(f'    * {item.get("itemName")} (ID: {item.get("itemId")})')
                
                self.stdout.write('\n--- Key Configuration Used ---')
                self.stdout.write(f'Store Name: https://bookefay.com')
                self.stdout.write(f'SKU = Item Name: {pill.pill_number}')
                self.stdout.write(f'User Email: mohamedaymab26@gmail.com')
                
            else:
                self.stdout.write(self.style.ERROR(f'✗ Order creation failed: {result["error"]}'))
                
        except Pill.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ Pill #{pill_id} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Exception: {e}'))
            
        self.stdout.write('\n=== Test Complete ===')
        
        # Usage instructions
        self.stdout.write('\n--- Usage Instructions ---')
        self.stdout.write('To test with different pill:')
        self.stdout.write(f'  python manage.py test_khazenly_updated --pill-id OTHER_ID')
        self.stdout.write('To test token only:')
        self.stdout.write(f'  python manage.py test_khazenly_updated --test-token')