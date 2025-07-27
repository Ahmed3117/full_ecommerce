from django.core.management.base import BaseCommand
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import User

class Command(BaseCommand):
    help = 'Get or create JWT token for production testing'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username', default='admin')
        parser.add_argument('--production', action='store_true', help='Generate token for production use')

    def handle(self, *args, **options):
        username = options['username']
        is_production = options['production']
        
        try:
            user = User.objects.get(username=username)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            if is_production:
                self.stdout.write(self.style.SUCCESS(f'✓ PRODUCTION JWT tokens generated for {username}'))
                self.stdout.write('=' * 60)
                self.stdout.write('COPY THIS TOKEN FOR PRODUCTION TESTING:')
                self.stdout.write('=' * 60)
            else:
                self.stdout.write(self.style.SUCCESS(f'✓ JWT tokens generated for {username}'))
            
            self.stdout.write(f'Access Token: {access_token}')
            if not is_production:
                self.stdout.write(f'Refresh Token: {refresh}')
            self.stdout.write(f'User ID: {user.id}')
            
            if is_production:
                self.stdout.write('=' * 60)
                self.stdout.write('⚠️  IMPORTANT: This token expires in 3 days')
                self.stdout.write('Use this token in your production testing')
                self.stdout.write('=' * 60)
            else:
                self.stdout.write('')
                self.stdout.write(self.style.WARNING('Use the Access Token in your Authorization header'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ User {username} not found'))