# api/webhooks.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import logging
from .models import Pill

logger = logging.getLogger(__name__)

@csrf_exempt
def fawaterak_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Fawaterak webhook received: {data}")
            
            invoice_key = data.get('invoice_key')
            payment_status = data.get('payment_status')
            
            if invoice_key and payment_status == 'paid':
                pill = Pill.objects.filter(fawaterak_invoice_key=invoice_key).first()
                if pill and not pill.paid:
                    pill.paid = True
                    pill.status = 'p'  # Paid status
                    pill.save()
                    
                    # Update inventory, send notifications, etc.
                    
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return JsonResponse({'status': 'error'}, status=400)
    
    return JsonResponse({'status': 'invalid method'}, status=405)