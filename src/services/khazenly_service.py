import requests
import json
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class KhazenlyAPIService:
    def __init__(self):
        self.base_url = settings.KHAZENLY_BASE_URL
        self.client_id = settings.KHAZENLY_CLIENT_ID
        self.client_secret = settings.KHAZENLY_CLIENT_SECRET
        self.store_name = settings.KHAZENLY_STORE_NAME  # Should be "BOOKIFAY"
        self.refresh_token = getattr(settings, 'KHAZENLY_REFRESH_TOKEN', '')
        
        self.token_url = f"{self.base_url}/selfservice/services/oauth2/token"
        self.create_order_url = f"{self.base_url}/services/apexrest/api/CreateOrder"
    
    def get_access_token(self):
        # Try cache first
        token = cache.get('khazenly_access_token')
        if token:
            logger.info("Using cached access token")
            return token
        
        # Use refresh token
        if self.refresh_token:
            logger.info("Getting new access token using refresh token")
            return self.refresh_access_token(self.refresh_token)
        
        logger.error("No refresh token available")
        return None
    
    def refresh_access_token(self, refresh_token):
        try:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            logger.info("Making refresh token request")
            response = requests.post(self.token_url, data=data, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Refresh token failed: {response.text}")
                return None
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            new_refresh_token = token_data.get('refresh_token')
            
            if access_token:
                cache.set('khazenly_access_token', access_token, timeout=23*60*60)
                if new_refresh_token:
                    self.refresh_token = new_refresh_token
                    cache.set('khazenly_refresh_token', new_refresh_token, timeout=None)
                
                logger.info("✓ Access token obtained successfully")
                return access_token
            else:
                logger.error("No access token in refresh response")
                return None
                
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
        return None
    
    def map_government_to_city(self, government):
        """Map government to valid Khazenly cities"""
        # Valid cities from Khazenly documentation
        valid_cities = [
            'Alexandria', 'Assiut', 'Aswan', 'Bani-Sweif', 'Behera', 'Cairo',
            'Dakahleya', 'Damietta', 'Fayoum', 'Giza', 'Hurghada', 'Ismailia',
            'Luxor', 'Mahalla', 'Mansoura', 'Marsa Matrouh', 'Menya', 'Monefeya',
            'North Coast', 'Port-Said', 'Qalyubia', 'Qena', 'Red Sea', 'Sharkeya',
            'Sohag', 'Suez', 'Tanta', 'Zagazig', 'Gharbeya', 'Kafr El Sheikh',
            'Al-Wadi Al-Gadid', 'Sharm El Sheikh', 'North Sinai', 'South Sinai'
        ]
        
        # If it's already a valid city name, return it
        if government in valid_cities:
            return government
        
        # Try mapping from codes or common names
        mapping = {
            'ca': 'Cairo', 'cairo': 'Cairo', '1': 'Cairo',
            'gz': 'Giza', 'giza': 'Giza', '2': 'Giza',
            'al': 'Alexandria', 'alexandria': 'Alexandria', '3': 'Alexandria',
            'as': 'Assiut', 'sw': 'Aswan', 'bs': 'Bani-Sweif',
            'bh': 'Behera', 'dk': 'Dakahleya', 'dm': 'Damietta',
            'fy': 'Fayoum', 'hr': 'Hurghada', 'is': 'Ismailia',
            'lx': 'Luxor', 'mh': 'Mahalla', 'mn': 'Mansoura',
            'mm': 'Marsa Matrouh', 'my': 'Menya', 'mf': 'Monefeya',
            'nc': 'North Coast', 'ps': 'Port-Said', 'ql': 'Qalyubia',
            'qn': 'Qena', 'rs': 'Red Sea', 'sh': 'Sharkeya',
            'sg': 'Sohag', 'sz': 'Suez', 'tn': 'Tanta',
            'zg': 'Zagazig', 'gh': 'Gharbeya', 'ks': 'Kafr El Sheikh',
            'wg': 'Al-Wadi Al-Gadid', 'se': 'Sharm El Sheikh',
            'ns': 'North Sinai', 'ss': 'South Sinai',
        }
        
        mapped_city = mapping.get(str(government).lower(), 'Cairo')
        logger.info(f"Mapped government '{government}' to city '{mapped_city}'")
        return mapped_city
    
    def create_order(self, pill):
        try:
            logger.info(f"=== Creating Khazenly order for pill {pill.pill_number} ===")
            
            # Validation
            if not hasattr(pill, 'pilladdress'):
                return {'success': False, 'error': 'Pill has no address information'}
            
            if not pill.items.exists():
                return {'success': False, 'error': 'Pill has no items'}
            
            address = pill.pilladdress
            
            # Validate required address fields
            if not address.phone:
                return {'success': False, 'error': 'Customer phone number is required'}
            
            if not address.address:
                return {'success': False, 'error': 'Customer address is required'}
            
            if not address.name:
                return {'success': False, 'error': 'Customer name is required'}
            
            access_token = self.get_access_token()
            if not access_token:
                return {'success': False, 'error': 'Could not get access token'}
            
            # Create line items
            line_items = []
            total_items_price = 0
            
            for item in pill.items.all():
                # Generate unique SKU
                sku = f"BOOKIFAY-{item.product.id}"
                if item.size:
                    sku += f"-{item.size}"
                if item.color:
                    sku += f"-{item.color.name.replace(' ', '').replace('-', '')}"
                
                unit_price = float(item.product.discounted_price())
                total_items_price += unit_price * item.quantity
                    
                line_items.append({
                    "SKU": sku,
                    "Price": unit_price,
                    "ItemId": str(item.product.id),
                    "ItemName": item.product.name[:100],  # Limit length
                    "Quantity": item.quantity,
                    "DiscountAmount": 0.0  # Individual item discount
                })
            
            # Calculate totals
            discount_amount = float(pill.coupon_discount + pill.calculate_gift_discount())
            shipping_fees = float(pill.shipping_price())
            tax_amount = 0.0  # Assuming no tax for now
            
            # Total amount calculation: items - discount + shipping + tax
            total_amount = total_items_price - discount_amount + shipping_fees + tax_amount
            invoice_total = float(pill.final_price())
            
            # Map city
            city = self.map_government_to_city(address.government)
            
            # Payment method and status
            if address.pay_method == 'c':
                payment_method = "Cash-on-Delivery"
                payment_status = "pending"
            else:
                payment_method = "Pre-Paid"
                payment_status = "paid" if pill.paid else "pending"
            
            # Build the payload according to Khazenly specification
            payload = {
                "Order": {
                    # Required Order fields
                    "orderId": pill.pill_number,
                    "totalAmount": total_amount,
                    "invoiceTotalAmount": invoice_total,
                    "taxAmount": tax_amount,
                    "orderNumber": pill.pill_number,
                    "paymentMethod": payment_method,
                    "weight": 1.0,  # Default weight in kg
                    "storeCurrency": "EGP",
                    "discountAmount": discount_amount,
                    "shippingFees": shipping_fees,
                    "storeName": self.store_name,  # "BOOKIFAY"
                    
                    # Optional Order fields
                    "paymentStatus": payment_status,
                    "isPickedByMerchant": False,
                    "merchantAWB": "",
                    "merchantCourier": "",
                    "merchantAwbDocument": "",
                    "additionalNotes": f"Order from Django - User: {pill.user.username}",
                    "noOfBoxes": 1
                },
                "Customer": {
                    # Required Customer fields
                    "Address1": address.address,
                    "City": city,
                    "Country": "Egypt",
                    "customerName": address.name,
                    "Tel": address.phone,
                    
                    # Optional Customer fields
                    "Address2": "",
                    "Address3": "",
                    "customerId": str(pill.user.id),
                    "secondaryTel": ""
                },
                "lineItems": line_items
            }
            
            # Log the payload for debugging
            logger.info(f"Store Name: {self.store_name}")
            logger.info(f"Total Items Price: {total_items_price}")
            logger.info(f"Discount Amount: {discount_amount}")
            logger.info(f"Shipping Fees: {shipping_fees}")
            logger.info(f"Total Amount: {total_amount}")
            logger.info(f"Invoice Total: {invoice_total}")
            logger.info(f"City: {city}")
            logger.info(f"Payment: {payment_method} - {payment_status}")
            
            logger.info("=== PAYLOAD ===")
            logger.info(json.dumps(payload, indent=2))
            
            # Make the API request
            headers = {
                'auth': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(self.create_order_url, json=payload, headers=headers, timeout=60)
            
            logger.info(f"Response Status: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('resultCode') == 0:  # Success
                    logger.info(f"✓ Khazenly order created successfully for pill {pill.pill_number}")
                    return {'success': True, 'data': response_data}
                else:
                    logger.error(f"Khazenly returned error: {response_data}")
                    return {'success': False, 'error': f"Khazenly error: {response_data.get('result', 'Unknown error')}"}
            else:
                logger.error(f"HTTP error: {response.status_code} - {response.text}")
                return {'success': False, 'error': f"HTTP {response.status_code}: {response.text}"}
            
        except Exception as e:
            logger.error(f"Exception creating order: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': f"Exception: {str(e)}"}

khazenly_service = KhazenlyAPIService()