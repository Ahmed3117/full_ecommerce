#!/usr/bin/env python3
import os
import sys
import django
import requests
import json

# Add the project directory to Python path
sys.path.append('/media/ahmedissa/AHMED4/mainwork/easytech/full_ecommerce/src')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Minimal Django setup for testing
try:
    django.setup()
except Exception as e:
    print(f"Django setup error (ignoring): {e}")

# Test Fawaterak API directly with token in payload
def test_fawaterak_token_in_payload():
    api_key = "1bdd1c4da30c752efc4e8bd523973e484d8f1c50714cff0b97"
    base_url = "https://app.fawaterk.com/api/v2"
    
    # Minimal test payload
    payload = {
        "token": api_key,  # Token in payload
        "cartTotal": "100.00",
        "currency": "EGP",
        "customer": {
            "first_name": "Test",
            "last_name": "Customer",
            "email": "test@example.com",
            "phone": "01234567890"
        },
        "cartItems": [{
            "name": "Test Product",
            "price": "100.00",
            "quantity": "1"
        }],
        "redirectionUrls": {
            "successUrl": "http://127.0.0.1:8000/success/",
            "failUrl": "http://127.0.0.1:8000/fail/",
            "pendingUrl": "http://127.0.0.1:8000/pending/"
        }
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    print("=== Testing Fawaterak with Token in Payload ===")
    print(f"URL: {base_url}/createInvoiceLink")
    print(f"Token (first 20 chars): {api_key[:20]}...")
    print(f"Payload keys: {list(payload.keys())}")
    
    try:
        response = requests.post(
            f"{base_url}/createInvoiceLink",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('status') == 'success':
                print("✅ SUCCESS: Token in payload format works!")
                return True
            else:
                print(f"❌ API Error: {response_data}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    test_fawaterak_token_in_payload()