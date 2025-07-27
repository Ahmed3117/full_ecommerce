from django.core.management.base import BaseCommand
from django.core.cache import cache
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check and debug Fawaterak webhook logs and payment status'

    def add_arguments(self, parser):
        parser.add_argument('--pill-number', type=str, help='Pill number to check', required=True)

    def handle(self, *args, **options):
        pill_number = options['pill_number']
        
        self.stdout.write('=== Fawaterak Payment Debug ===')
        self.stdout.write(f'Checking pill: {pill_number}')
        
        # Check if pill exists
        try:
            from products.models import Pill
            pill = Pill.objects.get(pill_number=pill_number)
            
            self.stdout.write(f'✓ Pill found: ID {pill.id}')
            self.stdout.write(f'  - Current paid status: {pill.paid}')
            self.stdout.write(f'  - Total amount: {pill.final_price()} EGP')
            self.stdout.write(f'  - User: {pill.user.username} (ID: {pill.user.id})')
            
        except Pill.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ Pill {pill_number} not found'))
            return
        
        # Check cached invoice data
        cached_data = cache.get(f'fawaterak_invoice_{pill_number}')
        if cached_data:
            self.stdout.write('✓ Cached invoice data found:')
            for key, value in cached_data.items():
                self.stdout.write(f'  - {key}: {value}')
        else:
            self.stdout.write('⚠ No cached invoice data found')
        
        # Try to get current status from Fawaterak
        from services.fawaterak_service import fawaterak_service
        
        if cached_data:
            self.stdout.write('\n--- Checking Fawaterak Status ---')
            result = fawaterak_service.get_invoice_status(pill_number)
            
            if result['success']:
                self.stdout.write('✓ Fawaterak status check successful:')
                status_data = result['data']
                for key, value in status_data.items():
                    self.stdout.write(f'  - {key}: {value}')
            else:
                self.stdout.write(f'✗ Fawaterak status check failed: {result["error"]}')
        
        # Show recent webhook logs (if any)
        self.stdout.write('\n--- Webhook Debug Info ---')
        self.stdout.write('Check your Django logs for webhook entries containing:')
        self.stdout.write(f'  - "Processing Fawaterak webhook" with pill_number: {pill_number}')
        self.stdout.write(f'  - Look for payment_method and status fields')
        
        # Manual payment confirmation option
        self.stdout.write('\n--- Manual Actions ---')
        self.stdout.write('If payment was actually completed but not reflected:')
        self.stdout.write(f'1. Run: python manage.py confirm_payment --pill-number {pill_number}')
        self.stdout.write('2. Or use the webhook simulation in your test page')
        
        self.stdout.write('\n=== Debug Complete ===')