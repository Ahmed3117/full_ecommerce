import requests
import json
import logging
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

class KhazenlyService:
    def __init__(self):
        # Updated configuration based on Khazenly feedback
        self.base_url = settings.KHAZENLY_BASE_URL
        self.client_id = settings.KHAZENLY_CLIENT_ID
        self.client_secret = settings.KHAZENLY_CLIENT_SECRET
        
        # FIXED: Use the correct store name as provided by Khazenly
        self.store_name = "https://bookefay.com"  # Updated from BOOKIFAY
        
        # FIXED: Use the correct user email for order creation
        self.order_user_email = "mohamedaymab26@gmail.com"  # Not the API user
        
        # Updated tokens from successful authentication
        self.refresh_token = settings.KHAZENLY_REFRESH_TOKEN
        
        # Cache keys
        self.access_token_cache_key = 'khazenly_access_token'
        self.token_expiry_cache_key = 'khazenly_token_expiry'

    def get_access_token(self):
        """
        Get valid access token, refresh if needed
        """
        try:
            # Check if we have a cached valid token
            cached_token = cache.get(self.access_token_cache_key)
            token_expiry = cache.get(self.token_expiry_cache_key)
            
            if cached_token and token_expiry:
                if datetime.now() < token_expiry:
                    return cached_token
            
            # Token expired or doesn't exist, refresh it
            logger.info("Refreshing Khazenly access token...")
            
            # FIXED: Use correct refresh token endpoint with /selfservice prefix from Postman collection
            token_url = f"{self.base_url}/selfservice/services/oauth2/token"
            
            token_data = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            logger.info(f"Making token request to: {token_url}")
            
            response = requests.post(token_url, data=token_data, headers=headers, timeout=30)
            
            logger.info(f"Token response status: {response.status_code}")
            logger.info(f"Token response: {response.text}")
            
            if response.status_code == 200:
                token_response = response.json()
                access_token = token_response.get('access_token')
                
                if access_token:
                    # Cache the token (expires in 2 hours by default)
                    expiry_time = datetime.now() + timedelta(hours=1, minutes=50)  # 10 min buffer
                    
                    cache.set(self.access_token_cache_key, access_token, timeout=6600)  # 1h 50m
                    cache.set(self.token_expiry_cache_key, expiry_time, timeout=6600)
                    
                    logger.info("✓ Access token refreshed and cached successfully")
                    return access_token
                else:
                    logger.error("No access_token in response")
                    return None
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception getting access token: {e}")
            return None

    def create_order(self, pill):
        """
        Create order in Khazenly with corrected configuration based on working Postman collection
        """
        try:
            logger.info(f"Creating Khazenly order for pill {pill.pill_number}")
            
            # Get valid access token
            access_token = self.get_access_token()
            if not access_token:
                return {'success': False, 'error': 'Failed to get access token'}
            
            # Validate pill has required data
            if not hasattr(pill, 'pilladdress'):
                return {'success': False, 'error': 'Pill address information missing'}
            
            address = pill.pilladdress
            
            # FIXED: Create unique order ID to avoid conflicts
            timestamp_suffix = int(timezone.now().timestamp())
            unique_order_id = f"{pill.pill_number}-{timestamp_suffix}"
            
            # Prepare line items with corrected format from Postman collection
            line_items = []
            total_product_price = 0
            
            for item in pill.items.all():
                item_price = float(item.product.discounted_price())
                total_product_price += item_price * item.quantity
                
                # FIXED: Use exact field names from working Postman collection
                line_items.append({
                    "sku": unique_order_id,  # Use unique order ID as SKU
                    "itemName": unique_order_id,  # Same as SKU per requirement
                    "price": item_price,  # lowercase as in collection
                    "quantity": item.quantity,  # lowercase as in collection
                    "discountAmount": 0,  # lowercase as in collection
                    "itemId": None  # lowercase as in collection
                })
            
            # Calculate amounts
            shipping_fees = float(pill.shipping_price())
            discount_amount = float(pill.coupon_discount + pill.calculate_gift_discount())
            total_amount = total_product_price + shipping_fees - discount_amount
            
            # FIXED: Use exact structure from working Postman collection
            order_data = {
                "Order": {
                    "orderId": unique_order_id,  # Use unique order ID
                    "orderNumber": unique_order_id,  # Use unique order ID
                    "storeName": self.store_name,  # https://bookefay.com
                    "totalAmount": total_amount,
                    "shippingFees": shipping_fees,
                    "discountAmount": discount_amount,
                    "taxAmount": 0,
                    "invoiceTotalAmount": total_amount,
                    "weight": 0,
                    "noOfBoxes": 1,
                    "paymentMethod": "Cash-on-Delivery",  # Exact string from collection
                    "paymentStatus": "pending",
                    "storeCurrency": "EGP",
                    "isPickedByMerchant": False,  # Boolean, not lowercase
                    "merchantAWB": "",
                    "merchantCourier": "",
                    "merchantAwbDocument": "",
                    "additionalNotes": f"Order for pill {pill.pill_number}"
                },
                "Customer": {
                    "customerName": address.name,
                    "tel": address.phone.replace('+', '').replace('-', '').replace(' ', '') if address.phone else "",  # lowercase 'tel'
                    "secondaryTel": "",  # lowercase with capital T
                    "address1": address.address,  # lowercase with number
                    "address2": "",
                    "address3": "",
                    "city": address.get_government_display(),  # lowercase 'city'
                    "country": "Egypt",  # lowercase 'country'
                    "customerId": None  # lowercase with capital I
                },
                "lineItems": line_items
            }
            
            # FIXED: Use correct API endpoint from Postman collection
            api_url = f"{self.base_url}/services/apexrest/api/CreateOrder"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            logger.info(f"Making order request to: {api_url}")
            logger.info(f"Order data: {json.dumps(order_data, indent=2)}")
            
            response = requests.post(api_url, json=order_data, headers=headers, timeout=60)
            
            logger.info(f"Khazenly order response status: {response.status_code}")
            logger.info(f"Khazenly order response: {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Check for success
                if response_data.get('resultCode') == 0:
                    order_info = response_data.get('order', {})
                    
                    logger.info(f"✓ Khazenly order created successfully: {order_info.get('salesOrderNumber')}")
                    
                    return {
                        'success': True,
                        'data': {
                            'khazenly_order_id': order_info.get('id'),
                            'sales_order_number': order_info.get('salesOrderNumber'),
                            'order_number': order_info.get('orderNumber'),
                            'line_items': response_data.get('lineItems', []),
                            'customer': response_data.get('customer', {}),
                            'raw_response': response_data
                        }
                    }
                else:
                    error_msg = response_data.get('message', 'Unknown error from Khazenly')
                    logger.error(f"Khazenly order creation failed: {error_msg}")
                    return {'success': False, 'error': error_msg}
            else:
                logger.error(f"HTTP error creating Khazenly order: {response.status_code} - {response.text}")
                return {'success': False, 'error': f'HTTP {response.status_code}: {response.text}'}
                
        except Exception as e:
            logger.error(f"Exception creating Khazenly order: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}

    def get_order_status(self, sales_order_number):
        """
        Get order status from Khazenly
        """
        try:
            access_token = self.get_access_token()
            if not access_token:
                return {'success': False, 'error': 'Failed to get access token'}
            
            # Construct status check URL
            status_url = f"{self.base_url}/services/apexrest/ExternalIntegrationWebService/orders/{sales_order_number}"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            logger.info(f"Checking order status: {status_url}")
            
            response = requests.get(status_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}: {response.text}'}
                
        except Exception as e:
            logger.error(f"Exception getting order status: {e}")
            return {'success': False, 'error': str(e)}

# Global instance
khazenly_service = KhazenlyService()