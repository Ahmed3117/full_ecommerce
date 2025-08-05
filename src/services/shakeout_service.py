import requests
import json
import logging
import hashlib
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

class ShakeoutService:
    def __init__(self):
        # Shake-out API configuration
        self.api_key = getattr(settings, 'SHAKEOUT_API_KEY', '68909b3acd8cbojjCbFOPPJlGvwVTHSWKXxehYTJeFEuATalS1U1D')
        self.secret_key = getattr(settings, 'SHAKEOUT_SECRET_KEY', '9aa639b63b2a4c3182f73771fb2e11df')
        self.base_url = getattr(settings, 'SHAKEOUT_BASE_URL', 'https://dash.shake-out.com/api/public/vendor')
        self.create_invoice_url = f"{self.base_url}/invoice"
        
        # Headers for API requests
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'apikey {self.api_key}'
        }
        
        logger.info("🔧 Shake-out Service initialized")
        logger.info(f"🔧 API Key loaded: {self.api_key[:10]}...")
        logger.info(f"🔧 Base URL: {self.base_url}")

    def calculate_invoice_amount(self, items, shipping=0, discount=0, discount_type='fixed', tax=0):
        """Calculate total invoice amount including shipping, discount, and tax"""
        subtotal = sum(float(item['price']) * int(item['quantity']) for item in items)
        
        if discount > 0:
            if discount_type == 'percent':
                discount_amount = subtotal * (discount / 100)
            else:
                discount_amount = discount
            subtotal -= discount_amount
        
        total = subtotal + shipping
        if tax > 0:
            total += total * (tax / 100)
        
        return round(total, 2)

    def create_payment_invoice(self, pill):
        """Create a payment invoice with Shake-out"""
        try:
            logger.info(f"Creating Shake-out invoice for pill {pill.pill_number}")
            
            # Check if pill already has a Shake-out invoice
            if pill.shakeout_invoice_id:
                logger.info(f"Pill {pill.pill_number} already has Shake-out invoice: {pill.shakeout_invoice_id}")
                
                # Return existing invoice data in unified format
                return {
                    'success': False,
                    'error': 'Pill already has a Shake-out invoice',
                    'data': {
                        'invoice_id': pill.shakeout_invoice_id,
                        'invoice_ref': pill.shakeout_invoice_ref,
                        'url': self._build_payment_url(pill.shakeout_invoice_id, pill.shakeout_invoice_ref),
                        'payment_url': self._build_payment_url(pill.shakeout_invoice_id, pill.shakeout_invoice_ref),
                        'created_at': pill.shakeout_created_at.isoformat() if pill.shakeout_created_at else None,
                        'status': 'active',  # Assume active if stored
                        'total_amount': float(pill.final_price()),
                        'currency': 'EGP'
                    }
                }
            
            # Get pill address
            pill_address = pill.pilladdress
            if not pill_address:
                return {
                    'success': False,
                    'error': 'Pill address information is required',
                    'data': None
                }
            
            # Format phone number for Shake-out (must be in format +201234567890)
            phone = pill_address.phone
            if phone and not phone.startswith('+'):
                # If phone starts with 0, replace with +20
                if phone.startswith('0'):
                    formatted_phone = '+2' + phone
                # If phone starts with 20, add +
                elif phone.startswith('20'):
                    formatted_phone = '+' + phone
                # Otherwise add +20
                else:
                    formatted_phone = '+20' + phone
            else:
                formatted_phone = phone or '+201234567890'  # Default fallback
            
            # Prepare customer data
            customer_data = {
                "first_name": pill_address.name.split()[0] if pill_address.name else "Customer",
                "last_name": " ".join(pill_address.name.split()[1:]) if pill_address.name and len(pill_address.name.split()) > 1 else "Name",
                "email": pill_address.email or f"customer_{pill.id}@bookefay.com",
                "phone": formatted_phone,
                "address": f"{pill_address.address or 'Cairo'}, {pill_address.government or 'Egypt'}"
            }
            
            # Calculate totals
            items_total = sum(item.product.discounted_price() * item.quantity for item in pill.items.all())
            shipping_cost = pill.shipping_price()
            total_discount = pill.calculate_coupon_discount() + pill.calculate_gift_discount()
            final_amount = pill.final_price()
            
            # Prepare invoice items (all prices must be positive)
            invoice_items = []
            
            # Add product items
            for item in pill.items.all():
                item_name = item.product.name
                if item.size:
                    item_name += f" (Size: {item.size}"
                    if item.color:
                        item_name += f", Color: {item.color.name})"
                    else:
                        item_name += ")"
                elif item.color:
                    item_name += f" (Color: {item.color.name})"
                
                invoice_items.append({
                    "name": item_name,
                    "price": float(item.product.discounted_price()),
                    "quantity": item.quantity
                })
            
            # Add shipping as separate item if exists
            if shipping_cost > 0:
                invoice_items.append({
                    "name": "Shipping Fee",
                    "price": float(shipping_cost),
                    "quantity": 1
                })
            
            # Handle discount differently - use Shake-out's discount system instead of negative items
            discount_enabled = total_discount > 0
            discount_value = float(total_discount) if discount_enabled else 0
            
            # Prepare invoice data
            invoice_data = {
                "amount": float(final_amount),
                "currency": "EGP",
                "due_date": (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                "customer": customer_data,
                "redirection_urls": {
                    "success_url": f"{settings.SUCCESS_URL}",
                    "fail_url": f"{settings.FAIL_URL}",
                    "pending_url": f"{settings.PENDING_URL}"
                },
                "invoice_items": invoice_items,
                "tax_enabled": False,
                "discount_enabled": discount_enabled,
                "discount_type": "fixed",
                "discount_value": discount_value
            }
            
            logger.info(f"Making request to: {self.base_url}")
            logger.info(f"Invoice data: {json.dumps(invoice_data, indent=2)}")
            logger.info("Redirect URLs:")
            logger.info(f"  Success: {invoice_data['redirection_urls']['success_url']}")
            logger.info(f"  Pending: {invoice_data['redirection_urls']['pending_url']}")
            logger.info(f"  Fail: {invoice_data['redirection_urls']['fail_url']}")
            
            # Make API request
            response = requests.post(
                self.create_invoice_url,
                json=invoice_data,
                headers=self.headers,
                timeout=30
            )
            
            logger.info(f"Shake-out response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Handle successful creation - unify response format
                if response_data.get('status') == 'success':
                    # Successful creation response format
                    data = response_data.get('data', {})
                    invoice_id = data.get('invoice_id')
                    invoice_ref = data.get('invoice_ref')
                    payment_url = data.get('url')
                    
                    return {
                        'success': True,
                        'message': response_data.get('message', 'Invoice created successfully'),
                        'data': {
                            'invoice_id': invoice_id,
                            'invoice_ref': invoice_ref,
                            'url': payment_url,
                            'payment_url': payment_url,  # Unified key name
                            'created_at': timezone.now().isoformat(),
                            'status': 'active',
                            'total_amount': float(final_amount),
                            'currency': 'EGP',
                            'raw_response': response_data
                        }
                    }
                else:
                    # Handle API error responses
                    return self._handle_api_error_response(response_data)
            else:
                # Handle HTTP errors
                try:
                    error_data = response.json()
                    return self._handle_api_error_response(error_data)
                except:
                    return {
                        'success': False,
                        'error': f'HTTP {response.status_code}: {response.text}',
                        'data': None
                    }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error creating Shake-out invoice: {str(e)}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'data': None
            }
        except Exception as e:
            logger.error(f"Unexpected error creating Shake-out invoice: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'data': None
            }

    def verify_webhook_signature(self, invoice_id, amount, invoice_status, updated_at, received_signature):
        """
        Verify webhook signature using SHA-256 hash
        """
        try:
            # Create the signature string as per Shake-out documentation
            signature_string = str(invoice_id) + str(amount) + str(invoice_status) + str(updated_at) + self.secret_key
            expected_signature = hashlib.sha256(signature_string.encode()).hexdigest()
            
            return expected_signature == received_signature
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False

    def check_payment_status(self, invoice_id):
        """
        Check payment status (if API supports it)
        Note: This might need to be implemented based on Shake-out's status check API
        """
        try:
            # This would need to be implemented if Shake-out provides a status check endpoint
            # For now, we rely on webhooks for status updates
            logger.info(f"Payment status check requested for invoice: {invoice_id}")
            return {'success': True, 'status': 'pending', 'message': 'Status check via webhooks only'}
        except Exception as e:
            logger.error(f"Exception checking payment status: {e}")
            return {'success': False, 'error': str(e)}

    def _handle_api_error_response(self, response_data):
        """Handle different API error response formats and unify them"""
        # Handle case where success=False in response
        if 'success' in response_data and not response_data['success']:
            data = response_data.get('data', {})
            
            return {
                'success': False,
                'error': response_data.get('error', 'Unknown API error'),
                'data': {
                    'invoice_id': data.get('invoice_id'),
                    'invoice_ref': data.get('invoice_ref'),
                    'url': data.get('payment_url') or self._build_payment_url(data.get('invoice_id'), data.get('invoice_ref')),
                    'payment_url': data.get('payment_url') or self._build_payment_url(data.get('invoice_id'), data.get('invoice_ref')),
                    'created_at': data.get('created_at'),
                    'status': data.get('status', 'unknown'),
                    'total_amount': None,  # Not provided in error responses
                    'currency': 'EGP'
                } if data else None
            }
        
        # Handle other error formats
        error_message = response_data.get('message') or response_data.get('error', 'Unknown API error')
        return {
            'success': False,
            'error': error_message,
            'data': None
        }

    def _build_payment_url(self, invoice_id, invoice_ref):
        """Build payment URL from invoice ID and reference"""
        if invoice_id and invoice_ref:
            return f"https://dash.shake-out.com/invoice/{invoice_id}/{invoice_ref}"
        return None

# Global instance
shakeout_service = ShakeoutService()