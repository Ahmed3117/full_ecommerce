from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
import json
import logging

from products.models import Pill
from services.fawaterak_service import fawaterak_service

logger = logging.getLogger(__name__)

class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pill_id):
        """
        Create a Fawaterak payment for a pill - JSON response only
        """
        try:
            pill = get_object_or_404(Pill, id=pill_id, user=request.user)
            
            # Check if pill is already paid
            if pill.paid:
                return Response({
                    'success': False,
                    'error': 'This order is already paid',
                    'pill_number': pill.pill_number,
                    'status': 'already_paid'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if pill has required data
            if not hasattr(pill, 'pilladdress'):
                return Response({
                    'success': False,
                    'error': 'Please complete your address information first',
                    'pill_number': pill.pill_number,
                    'status': 'missing_address'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create payment invoice
            result = fawaterak_service.create_payment_invoice(pill)
            
            if result['success']:
                return Response({
                    'success': True,
                    'message': 'Payment invoice created successfully',
                    'data': {
                        'payment_url': result['data']['payment_url'],
                        'invoice_id': result['data']['invoice_id'],
                        'reference_id': result['data']['reference_id'],
                        'total_amount': result['data']['total_amount'],
                        'pill_number': pill.pill_number,
                        'currency': 'EGP'
                    },
                    'status': 'payment_created'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': result['error'],
                    'pill_number': pill.pill_number,
                    'status': 'creation_failed'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error creating payment for pill {pill_id}: {e}")
            return Response({
                'success': False,
                'error': 'An error occurred while creating payment',
                'status': 'server_error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
@permission_classes([])  # No authentication required for webhooks
def fawaterak_webhook(request):
    """
    Handle Fawaterak payment webhooks - JSON response
    """
    try:
        # Get the webhook data
        webhook_data = request.data if hasattr(request, 'data') else json.loads(request.body.decode('utf-8'))
        
        logger.info(f"Received Fawaterak webhook: {webhook_data}")
        
        # Process the payment
        result = fawaterak_service.process_webhook_payment(webhook_data)
        
        if result['success']:
            return Response({
                'success': True,
                'message': 'Webhook processed successfully',
                'data': result['data']
            }, status=status.HTTP_200_OK)
        else:
            logger.error(f"Webhook processing failed: {result['error']}")
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook")
        return Response({
            'success': False,
            'error': 'Invalid JSON format'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Exception in webhook: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentSuccessView(APIView):
    permission_classes = []  # No authentication required for callbacks
    
    def get(self, request, pill_number):
        """
        Handle successful payment return - JSON response
        """
        try:
            pill = get_object_or_404(Pill, pill_number=pill_number)
            
            # Verify payment status from Fawaterak
            result = fawaterak_service.get_invoice_status(pill_number)
            
            if result['success']:
                invoice_data = result['data']
                payment_status = invoice_data.get('status', '').lower()
                
                if payment_status in ['paid', 'success', 'completed']:
                    pill.paid = True
                    pill.save()
                    
                    return Response({
                        'success': True,
                        'message': 'Payment confirmed successfully',
                        'data': {
                            'pill_number': pill.pill_number,
                            'payment_status': 'confirmed',
                            'total_amount': float(pill.final_price()),
                            'currency': 'EGP',
                            'paid_at': invoice_data.get('paid_at'),
                            'invoice_data': invoice_data
                        },
                        'status': 'payment_confirmed'
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'message': 'Payment is still being processed',
                        'data': {
                            'pill_number': pill.pill_number,
                            'payment_status': payment_status,
                            'total_amount': float(pill.final_price()),
                            'currency': 'EGP'
                        },
                        'status': 'payment_pending'
                    }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'Could not verify payment status',
                    'data': {
                        'pill_number': pill.pill_number,
                        'total_amount': float(pill.final_price())
                    },
                    'status': 'verification_failed'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error in payment success: {e}")
            return Response({
                'success': False,
                'error': 'An error occurred while verifying payment',
                'status': 'server_error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentFailedView(APIView):
    permission_classes = []  # No authentication required for callbacks
    
    def get(self, request, pill_number):
        """
        Handle failed payment return - JSON response
        """
        try:
            pill = get_object_or_404(Pill, pill_number=pill_number)
            
            # Get more details about the failure
            result = fawaterak_service.get_invoice_status(pill_number)
            failure_reason = "Unknown"
            
            if result['success']:
                invoice_data = result['data']
                failure_reason = invoice_data.get('status', 'failed')
            
            return Response({
                'success': False,
                'message': 'Payment failed',
                'data': {
                    'pill_number': pill.pill_number,
                    'payment_status': 'failed',
                    'failure_reason': failure_reason,
                    'total_amount': float(pill.final_price()),
                    'currency': 'EGP',
                    'retry_available': True
                },
                'status': 'payment_failed'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in payment failed: {e}")
            return Response({
                'success': False,
                'error': 'An error occurred while processing failed payment',
                'status': 'server_error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentPendingView(APIView):
    permission_classes = []  # No authentication required for callbacks
    
    def get(self, request, pill_number):
        """
        Handle pending payment return - JSON response
        """
        try:
            pill = get_object_or_404(Pill, pill_number=pill_number)
            
            # Check current status
            result = fawaterak_service.get_invoice_status(pill_number)
            current_status = "pending"
            
            if result['success']:
                invoice_data = result['data']
                current_status = invoice_data.get('status', 'pending')
            
            return Response({
                'success': True,
                'message': 'Payment is being processed',
                'data': {
                    'pill_number': pill.pill_number,
                    'payment_status': current_status,
                    'total_amount': float(pill.final_price()),
                    'currency': 'EGP',
                    'estimated_processing_time': '5-10 minutes',
                    'check_status_url': f'/products/api/payment/status/{pill.id}/'
                },
                'status': 'payment_pending'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in payment pending: {e}")
            return Response({
                'success': False,
                'error': 'An error occurred while checking pending payment',
                'status': 'server_error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CheckPaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pill_id):
        """
        AJAX endpoint to check payment status - JSON response
        """
        try:
            pill = get_object_or_404(Pill, id=pill_id, user=request.user)
            
            if pill.paid:
                return Response({
                    'success': True,
                    'message': 'Payment confirmed',
                    'data': {
                        'pill_number': pill.pill_number,
                        'paid': True,
                        'status': 'confirmed',
                        'total_amount': float(pill.final_price()),
                        'currency': 'EGP'
                    }
                }, status=status.HTTP_200_OK)
            
            # Check with Fawaterak
            result = fawaterak_service.get_invoice_status(pill.pill_number)
            
            if result['success']:
                invoice_data = result['data']
                payment_status = invoice_data.get('status', '').lower()
                
                if payment_status in ['paid', 'success', 'completed']:
                    pill.paid = True
                    pill.save()
                    
                    return Response({
                        'success': True,
                        'message': 'Payment confirmed',
                        'data': {
                            'pill_number': pill.pill_number,
                            'paid': True,
                            'status': 'confirmed',
                            'total_amount': float(pill.final_price()),
                            'currency': 'EGP',
                            'paid_at': invoice_data.get('paid_at')
                        }
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': True,
                        'message': 'Payment still processing',
                        'data': {
                            'pill_number': pill.pill_number,
                            'paid': False,
                            'status': payment_status,
                            'total_amount': float(pill.final_price()),
                            'currency': 'EGP'
                        }
                    }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': result['error'],
                    'data': {
                        'pill_number': pill.pill_number,
                        'paid': False,
                        'status': 'unknown'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return Response({
                'success': False,
                'error': 'Error checking payment status',
                'status': 'server_error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Instantiate the views
create_payment_view = CreatePaymentView.as_view()
payment_success_view = PaymentSuccessView.as_view()
payment_failed_view = PaymentFailedView.as_view()
payment_pending_view = PaymentPendingView.as_view()
check_payment_status_view = CheckPaymentStatusView.as_view()