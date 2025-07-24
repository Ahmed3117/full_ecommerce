#!/usr/bin/env python3
import requests
import json

def test_fawaterak_authentication():
    api_key = "1bdd1c4da30c752efc4e8bd523973e484d8f1c50714cff0b97"
    base_url = "https://app.fawaterk.com/api/v2"
    
    print("=== Testing Different Fawaterak Authentication Methods ===")
    
    # Test 1: Try login endpoint first
    print("\n--- Test 1: Login Authentication ---")
    login_payload = {
        "username": "mohamedaymab26@gmail.com",
        "password": "1234"
    }
    
    try:
        login_response = requests.post(
            f"{base_url}/login",
            json=login_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        print(f"Login Status: {login_response.status_code}")
        print(f"Login Response: {login_response.text}")
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            if login_data.get('status') == 'success':
                auth_token = login_data.get('data', {}).get('token')
                print(f"✓ Login successful, token: {auth_token[:20] if auth_token else 'None'}...")
                
                # Test creating invoice with login token
                test_invoice_with_token(base_url, auth_token, "login_token")
    except Exception as e:
        print(f"Login failed: {e}")
    
    # Test 2: Try with API key as Authorization header
    print("\n--- Test 2: API Key in Authorization Header ---")
    test_invoice_with_headers(base_url, api_key, "Authorization", f"Bearer {api_key}")
    
    # Test 3: Try with API key in custom header
    print("\n--- Test 3: API Key in Custom Headers ---")
    test_invoice_with_headers(base_url, api_key, "X-API-KEY", api_key)
    test_invoice_with_headers(base_url, api_key, "api-key", api_key)
    test_invoice_with_headers(base_url, api_key, "fawaterak-token", api_key)
    
    # Test 4: Try form data instead of JSON
    print("\n--- Test 4: Form Data with Token ---")
    test_invoice_form_data(base_url, api_key)

def test_invoice_with_token(base_url, token, token_type):
    payload = {
        "token": token,
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
    
    try:
        response = requests.post(
            f"{base_url}/createInvoiceLink",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        print(f"{token_type} - Status: {response.status_code}, Response: {response.text[:100]}...")
        return response.status_code == 200 and 'success' in response.text
    except Exception as e:
        print(f"{token_type} - Error: {e}")
        return False

def test_invoice_with_headers(base_url, api_key, header_name, header_value):
    payload = {
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
        'Content-Type': 'application/json',
        header_name: header_value
    }
    
    try:
        response = requests.post(
            f"{base_url}/createInvoiceLink",
            json=payload,
            headers=headers,
            timeout=30
        )
        print(f"{header_name} - Status: {response.status_code}, Response: {response.text[:100]}...")
        return response.status_code == 200 and 'success' in response.text
    except Exception as e:
        print(f"{header_name} - Error: {e}")
        return False

def test_invoice_form_data(base_url, api_key):
    payload = {
        'token': api_key,
        'cartTotal': '100.00',
        'currency': 'EGP',
        'customer[first_name]': 'Test',
        'customer[last_name]': 'Customer',
        'customer[email]': 'test@example.com',
        'customer[phone]': '01234567890',
        'cartItems[0][name]': 'Test Product',
        'cartItems[0][price]': '100.00',
        'cartItems[0][quantity]': '1',
        'redirectionUrls[successUrl]': 'http://127.0.0.1:8000/success/',
        'redirectionUrls[failUrl]': 'http://127.0.0.1:8000/fail/',
        'redirectionUrls[pendingUrl]': 'http://127.0.0.1:8000/pending/'
    }
    
    try:
        response = requests.post(
            f"{base_url}/createInvoiceLink",
            data=payload,
            timeout=30
        )
        print(f"Form Data - Status: {response.status_code}, Response: {response.text[:100]}...")
        return response.status_code == 200 and 'success' in response.text
    except Exception as e:
        print(f"Form Data - Error: {e}")
        return False

if __name__ == "__main__":
    test_fawaterak_authentication()