import json
import logging
import hashlib
import base64
import hmac
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.conf import settings
from products.models import Pill
from django.utils import timezone

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET", "POST", "HEAD"])
def khazenly_order_status_webhook(request):
    """
    Khazenly Order Status Update Webhook Handler
    
    GET: Health check for monitoring services  
    POST: Actual webhook processing
    """
    
    # Handle GET requests (health checks from monitoring services)
    if request.method == 'GET':
        logger.info("GET request received - Health check")
        return JsonResponse({
            'status': 'ok',
            'message': 'Khazenly webhook endpoint is healthy',
            'method': 'GET',
            'timestamp': timezone.now().isoformat(),
            'endpoint': 'khazenly-order-status-webhook'
        }, status=200)
    
    # Handle POST requests (actual webhooks)
    if request.method == 'POST':
        return handle_khazenly_webhook_post(request)

def handle_khazenly_webhook_post(request):
    """
    Handle actual Khazenly webhook POST requests
    """
    try:
        # Log the incoming webhook
        logger.info("=== Khazenly Webhook Received ===")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Body: {request.body.decode('utf-8')}")
        
        # FIXED: Check for correct HMAC header name from Khazenly
        hmac_header = request.headers.get('khazenly-hmac-sha256') or request.headers.get('Khazenly-Hmac-Sha256')
        
        # Verify HMAC signature for webhook security
        if hasattr(settings, 'KHAZENLY_WEBHOOK_SECRET') and settings.KHAZENLY_WEBHOOK_SECRET:
            logger.info(f"HMAC verification enabled. Header present: {bool(hmac_header)}")
            
            if hmac_header:
                if not verify_webhook_signature(request.body, hmac_header, settings.KHAZENLY_WEBHOOK_SECRET):
                    logger.error("❌ Invalid webhook signature - potential security threat!")
                    return JsonResponse({'error': 'Invalid signature'}, status=401)
                else:
                    logger.info("✅ Webhook signature verified successfully")
            else:
                logger.warning("⚠️ HMAC secret configured but no signature header received")
        else:
            logger.info("ℹ️ HMAC verification disabled (no secret configured)")
        
        # Parse the webhook payload
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        # Extract webhook data
        status = payload.get('status')
        order_reference = payload.get('orderReference')  # Khazenly order number (KH-BOOKIFAY-xxxxx)
        merchant_reference = payload.get('merchantReference')  # Our order ID
        order_supplier_id = payload.get('orderSupplierId')
        order_type = payload.get('orderType', 'New Order')
        store = payload.get('store')
        
        logger.info(f"Webhook Data - Status: {status}, Order Ref: {order_reference}, Merchant Ref: {merchant_reference}")
        
        # Validate required fields
        if not status or not order_reference:
            logger.error("Missing required fields: status or orderReference")
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # FIXED: Improved pill lookup logic
        pill = find_pill_from_webhook_data(order_reference, merchant_reference, order_supplier_id)
        
        if not pill:
            logger.warning(f"No pill found for order reference: {order_reference}, merchant reference: {merchant_reference}")
            # Return success to prevent webhook retries, but log the issue
            return JsonResponse({
                'success': True,
                'message': 'Order not found in system',
                'order_reference': order_reference,
                'merchant_reference': merchant_reference
            }, status=200)
        
        # Update pill status based on Khazenly status
        pill_status_updated = update_pill_status_from_khazenly(pill, status)
        
        # Log the status update
        logger.info(f"Processing webhook for Pill #{pill.pill_number}")
        logger.info(f"Khazenly Status: {status}")
        logger.info(f"Pill Status Updated: {pill_status_updated}")
        
        # Store webhook data for audit trail
        store_webhook_data(pill, payload)
        
        # Send success response
        response_data = {
            'success': True,
            'pill_id': pill.id,
            'pill_number': pill.pill_number,
            'status_updated': pill_status_updated,
            'current_status': pill.get_status_display(),
            'khazenly_status': status
        }
        
        logger.info(f"Webhook processed successfully: {response_data}")
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Error processing Khazenly webhook: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

def find_pill_from_webhook_data(order_reference, merchant_reference, order_supplier_id):
    """
    FIXED: Enhanced pill lookup logic to handle different reference formats
    """
    pill = None
    
    # Method 1: Try to find by Khazenly sales order number
    if order_reference:
        pill = Pill.objects.filter(khazenly_sales_order_number=order_reference).first()
        if pill:
            logger.info(f"Found pill by khazenly_sales_order_number: {order_reference}")
            return pill
    
    # Method 2: Try to find by stored Khazenly order number  
    if order_reference:
        pill = Pill.objects.filter(khazenly_order_number=order_reference).first()
        if pill:
            logger.info(f"Found pill by khazenly_order_number: {order_reference}")
            return pill
    
    # Method 3: Parse merchant reference to extract pill number
    # Format: "32344218672684726125-1753816161" -> extract "32344218672684726125"
    if merchant_reference:
        base_pill_number = merchant_reference.split('-')[0] if '-' in merchant_reference else merchant_reference
        pill = Pill.objects.filter(pill_number=base_pill_number).first()
        if pill:
            logger.info(f"Found pill by extracted pill_number: {base_pill_number}")
            return pill
    
    # Method 4: Try order_supplier_id if different from merchant_reference
    if order_supplier_id and order_supplier_id != merchant_reference:
        base_supplier_id = order_supplier_id.split('-')[0] if '-' in order_supplier_id else order_supplier_id
        pill = Pill.objects.filter(pill_number=base_supplier_id).first()
        if pill:
            logger.info(f"Found pill by extracted order_supplier_id: {base_supplier_id}")
            return pill
    
    # Method 5: Try exact match on pill_number with full merchant reference
    if merchant_reference:
        pill = Pill.objects.filter(pill_number=merchant_reference).first()
        if pill:
            logger.info(f"Found pill by exact merchant_reference: {merchant_reference}")
            return pill
    
    logger.warning(f"No pill found using any method for: order_ref={order_reference}, merchant_ref={merchant_reference}, supplier_id={order_supplier_id}")
    return None

# Keep all your other functions unchanged:
def verify_webhook_signature(payload, signature, secret):
    """
    Verify HMAC signature for webhook security
    """
    try:
        # Compute HMAC
        computed_signature = base64.b64encode(
            hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        return hmac.compare_digest(signature, computed_signature)
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False

def update_pill_status_from_khazenly(pill, khazenly_status):
    """
    Update pill status based on Khazenly order status
    """
    try:
        old_status = pill.status
        new_status = old_status  # Default: no change
        
        # Map Khazenly statuses to our pill statuses
        if khazenly_status in ["Out for Delivery"]:
            new_status = 'u'  # Under Delivery
        elif khazenly_status in ["Order Delivered"]:
            new_status = 'd'  # Delivered
        elif khazenly_status in ["Order Delivery Failed", "Returned to Fulfilment Center"]:
            new_status = 'r'  # Refused
        elif khazenly_status in ["Cancelled", "Voided", "Deleted"]:
            new_status = 'c'  # Canceled
        # Add more mappings as needed
        
        # Update status if changed
        if new_status != old_status:
            pill.status = new_status
            pill.save()
            
            logger.info(f"Updated Pill #{pill.pill_number} status from {old_status} to {new_status}")
            return True
        else:
            logger.info(f"No status change needed for Pill #{pill.pill_number} (current: {old_status})")
            return False
            
    except Exception as e:
        logger.error(f"Error updating pill status: {e}")
        return False

def store_webhook_data(pill, payload):
    """
    Store webhook data in pill's khazenly_data for audit trail
    """
    try:
        # Get existing data or create new
        existing_data = pill.khazenly_data or {}
        
        # Add webhook data
        if 'webhooks' not in existing_data:
            existing_data['webhooks'] = []
        
        webhook_entry = {
            'timestamp': timezone.now().isoformat(),
            'status': payload.get('status'),
            'order_reference': payload.get('orderReference'),
            'merchant_reference': payload.get('merchantReference'),
            'order_type': payload.get('orderType'),
            'payload': payload
        }
        
        existing_data['webhooks'].append(webhook_entry)
        
        # Keep only last 20 webhooks to avoid bloating
        if len(existing_data['webhooks']) > 20:
            existing_data['webhooks'] = existing_data['webhooks'][-20:]
        
        # Update the pill
        pill.khazenly_data = existing_data
        pill.save(update_fields=['khazenly_data'])
        
        logger.info(f"Stored webhook data for Pill #{pill.pill_number}")
        
    except Exception as e:
        logger.error(f"Error storing webhook data: {e}")