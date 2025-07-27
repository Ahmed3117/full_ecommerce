from django.core.management.base import BaseCommand
from django.core.cache import cache

class Command(BaseCommand):
    help = 'Manually confirm a payment that was actually completed'

    def add_arguments(self, parser):
        parser.add_argument('--pill-number', type=str, help='Pill number to confirm', required=True)
        parser.add_argument('--force', action='store_true', help='Force confirmation even if already paid')

    def handle(self, *args, **options):
        pill_number = options['pill_number']
        force = options['force']
        
        self.stdout.write('=== Manual Payment Confirmation ===')
        self.stdout.write(f'Confirming payment for pill: {pill_number}')
        
        try:
            from products.models import Pill
            pill = Pill.objects.get(pill_number=pill_number)
            
            if pill.paid and not force:
                self.stdout.write(self.style.WARNING(f'⚠ Pill {pill_number} is already marked as paid'))
                self.stdout.write('Use --force flag to confirm anyway')
                return
            
            # Mark as paid
            pill.paid = True
            pill.save()
            
            # Clear cached invoice data
            cache.delete(f'fawaterak_invoice_{pill_number}')
            
            self.stdout.write(self.style.SUCCESS(f'✓ Payment confirmed for pill {pill_number}'))
            self.stdout.write(f'  - User: {pill.user.username}')
            self.stdout.write(f'  - Amount: {pill.final_price()} EGP')
            self.stdout.write(f'  - Status updated: {pill.paid}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error confirming payment: {e}'))