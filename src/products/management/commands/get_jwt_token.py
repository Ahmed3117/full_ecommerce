from django.core.management.base import BaseCommand
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import User

class Command(BaseCommand):
    help = 'Get or create JWT token for user'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username', default='admin')

    def handle(self, *args, **options):
        username = options['username']
        
        try:
            user = User.objects.get(username=username)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            self.stdout.write(self.style.SUCCESS(f'✓ JWT tokens generated for {username}'))
            self.stdout.write(f'Access Token: {access_token}')
            self.stdout.write(f'Refresh Token: {refresh}')
            self.stdout.write(f'User ID: {user.id}')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Use the Access Token in your Authorization header'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ User {username} not found'))