from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Show Fawaterak test card information'

    def handle(self, *args, **options):
        self.stdout.write('=== Fawaterak Test Cards ===')
        self.stdout.write('\n✅ SUCCESS CARDS:')
        
        success_cards = [
            {'number': '5123450000000008', 'expiry': '12/26', 'cvv': '100', 'name': 'Fawaterak test'},
            {'number': '4005550000000001', 'expiry': '12/26', 'cvv': '100', 'name': 'Fawaterak test'},
            {'number': '4012000033330026', 'expiry': '12/26', 'cvv': '100', 'name': 'Fawaterak test'},
        ]
        
        for card in success_cards:
            self.stdout.write(f"  Card: {card['number']}")
            self.stdout.write(f"  Expiry: {card['expiry']}")
            self.stdout.write(f"  CVV: {card['cvv']}")
            self.stdout.write(f"  Name: {card['name']}")
            self.stdout.write("")
        
        self.stdout.write('❌ FAILURE CARDS (for testing failures):')
        
        failure_cards = [
            {'number': '5543474002249996', 'expiry': '05/21', 'cvv': '123', 'name': 'Fawaterak test'},
            {'number': '4000000000000069', 'expiry': '12/25', 'cvv': '100', 'name': 'Fawaterak test'},
        ]
        
        for card in failure_cards:
            self.stdout.write(f"  Card: {card['number']}")
            self.stdout.write(f"  Expiry: {card['expiry']}")
            self.stdout.write(f"  CVV: {card['cvv']}")
            self.stdout.write(f"  Name: {card['name']}")
            self.stdout.write("")
        
        self.stdout.write('💡 TIPS:')
        self.stdout.write('1. Always use "Fawaterak test" as cardholder name')
        self.stdout.write('2. Try success cards first')
        self.stdout.write('3. If still failing, check with Fawaterak support')