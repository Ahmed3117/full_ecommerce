from django.core.management.base import BaseCommand
import requests
from django.conf import settings

class Command(BaseCommand):
    help = 'Exchange Khazenly authorization code for refresh token'

    def add_arguments(self, parser):
        parser.add_argument('--auth-code', type=str, help='Authorization code from Khazenly', required=True)

    def handle(self, *args, **options):
        auth_code = options['auth_code']
        
        self.stdout.write('=== Khazenly Token Exchange ===')
        self.stdout.write(f'Exchanging authorization code for tokens...')
        
        try:
            # Token exchange URL
            token_url = f"{settings.KHAZENLY_BASE_URL}/services/oauth2/token"
            
            # Token exchange data
            token_data = {
                'grant_type': 'authorization_code',
                'client_id': settings.KHAZENLY_CLIENT_ID,
                'client_secret': settings.KHAZENLY_CLIENT_SECRET,
                'redirect_uri': 'https://khazenly4--test.sandbox.my.site.com/services/oauth2/success',
                'code': auth_code
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            self.stdout.write(f'Making request to: {token_url}')
            
            response = requests.post(token_url, data=token_data, headers=headers, timeout=30)
            
            self.stdout.write(f'Response status: {response.status_code}')
            
            if response.status_code == 200:
                token_response = response.json()
                
                access_token = token_response.get('access_token')
                refresh_token = token_response.get('refresh_token')
                
                self.stdout.write(self.style.SUCCESS('✓ Token exchange successful!'))
                self.stdout.write('')
                self.stdout.write('=== UPDATE YOUR .env FILE ===')
                self.stdout.write(f'KHAZENLY_REFRESH_TOKEN={refresh_token}')
                self.stdout.write('')
                self.stdout.write('=== FOR TESTING (expires soon) ===')
                self.stdout.write(f'Access Token: {access_token}')
                self.stdout.write('')
                self.stdout.write('Copy the refresh token above and update your .env file!')
                
            else:
                self.stdout.write(self.style.ERROR(f'✗ Token exchange failed: {response.status_code}'))
                self.stdout.write(f'Response: {response.text}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Exception: {e}'))