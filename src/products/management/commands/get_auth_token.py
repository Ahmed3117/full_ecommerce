from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

from accounts.models import User

class Command(BaseCommand):
    help = 'Get or create auth token for user'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username', default='admin')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
            token, created = Token.objects.get_or_create(user=user)
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ New token created for {username}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'✓ Existing token for {username}'))
            
            self.stdout.write(f'Token: {token.key}')
            self.stdout.write(f'User ID: {user.id}')
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ User {username} not found'))