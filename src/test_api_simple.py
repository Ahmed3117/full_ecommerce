import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

def test_khazenly_simple():
    # Get access token
    token_url = f"{os.getenv('KHAZENLY_BASE_URL')}/selfservice/services/oauth2/token"
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': os.getenv('KHAZENLY_REFRESH_TOKEN'),
        'client_id': os.getenv('KHAZENLY_CLIENT_ID'),
        'client_secret': os.getenv('KHAZENLY_CLIENT_SECRET')
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        print(f"Token failed: {response.text}")
        return
    
    access_token = response.json().get('access_token')
    print(f"✓ Got access token: {access_token[:20]}...")
    
    # Test very simple order
    headers = {
        'auth': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Ultra minimal payload
    test_payload = {
        "Order": {
            "orderId": "SIMPLE-TEST-001",
            "storeName": os.getenv('KHAZENLY_STORE_NAME'),
            "totalAmount": 100
        },
        "Customer": {
            "customerName": "Test User"
        },
        "lineItems": []
    }
    
    create_url = f"{os.getenv('KHAZENLY_BASE_URL')}/services/apexrest/api/CreateOrder"
    response = requests.post(create_url, json=test_payload, headers=headers)
    
    print(f"Response: {response.status_code}")
    print(f"Body: {response.text}")

if __name__ == "__main__":
    test_khazenly_simple()