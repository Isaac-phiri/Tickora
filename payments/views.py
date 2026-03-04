from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction, models
from django.conf import settings
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
import stripe
import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from .pasapal_service import PesaPalService

from django.views import View

from .models import Payment
from orders.models import Order
from tickets.models import Ticket
from django.utils.decorators import method_decorator
import logging
import uuid

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

pesapal = PesaPalService()

def payment_process(request, order_id):
    """
    Process payment for an order
    """
    order = get_object_or_404(
        Order.objects.select_related('event'),
        id=order_id,
        status='pending'
    )
    
    # Check if order is expired
    if order.is_expired:
        messages.error(request, 'This order has expired. Please start over.')
        return redirect('orders:cart_detail')
    
    if request.method == 'POST':
        payment_method_id = request.POST.get('payment_method_id')
        
        try:
            with transaction.atomic():
                # Create payment intent
                intent = stripe.PaymentIntent.create(
                    amount=int(order.total_amount * 100),  # Convert to cents
                    currency='usd',
                    payment_method=payment_method_id,
                    confirmation_method='manual',
                    confirm=True,
                    metadata={
                        'order_id': order.id,
                        'order_number': order.order_number,
                        'email': order.email,
                    }
                )
                
                # Create payment record
                payment = Payment.objects.create(
                    order=order,
                    user=order.user,
                    transaction_id=intent.id,
                    gateway='stripe',
                    amount=order.total_amount,
                    currency='usd',
                    payment_method=order.payment_method or 'credit_card',
                    status='processing',
                    gateway_response=intent,
                )
                
                # Handle payment result
                if intent.status == 'succeeded':
                    payment.status = 'completed'
                    payment.save()
                    
                    order.status = 'paid'
                    order.payment_date = timezone.now()
                    order.save()
                    
                    # Send confirmation emails
                    send_order_confirmation(order)
                    
                    return JsonResponse({
                        'success': True,
                        'redirect_url': reverse('orders:order_confirmation', args=[order.id])
                    })
                    
                elif intent.status == 'requires_action':
                    return JsonResponse({
                        'requires_action': True,
                        'payment_intent_client_secret': intent.client_secret
                    })
                    
                else:
                    payment.status = 'failed'
                    payment.save()
                    
                    return JsonResponse({
                        'error': 'Payment failed. Please try again.'
                    }, status=400)
                    
        except stripe.error.CardError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except stripe.error.StripeError as e:
            return JsonResponse({'error': 'Payment processing error. Please try again.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    # GET request - show payment form
    context = {
        'order': order,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, 'payments/payments.html', context)


@csrf_exempt
def stripe_webhook(request):
    """
    Handle Stripe webhooks
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_payment_success(payment_intent)
        
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        handle_payment_failure(payment_intent)
    
    return HttpResponse(status=200)


def handle_payment_success(payment_intent):
    """
    Handle successful payment
    """
    try:
        payment = Payment.objects.get(transaction_id=payment_intent['id'])
        payment.status = 'completed'
        payment.save()
        
        order = payment.order
        order.status = 'paid'
        order.payment_date = timezone.now()
        order.save()
        
        # Send confirmation email
        send_order_confirmation(order)
        
    except Payment.DoesNotExist:
        pass


def handle_payment_failure(payment_intent):
    """
    Handle failed payment
    """
    try:
        payment = Payment.objects.get(transaction_id=payment_intent['id'])
        payment.status = 'failed'
        payment.error_message = payment_intent.get('last_payment_error', {}).get('message', '')
        payment.save()
        
    except Payment.DoesNotExist:
        pass


def send_order_confirmation(order):
    """
    Send order confirmation email
    """
    subject = f'Order Confirmation - {order.order_number}'
    
    context = {
        'order': order,
    }
    
    html_message = render_to_string('emails/order_confirmation.html', context)
    plain_message = render_to_string('emails/order_confirmation.txt', context)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [order.email],
        html_message=html_message,
        fail_silently=True,
    )


def payment_success(request, order_id):
    """
    Payment success page
    """
    order = get_object_or_404(Order, id=order_id)
    return redirect('orders:order_confirmation', order_id=order.id)


def payment_cancel(request, order_id):
    """
    Payment cancelled page
    """
    order = get_object_or_404(Order, id=order_id)
    messages.warning(request, 'Payment was cancelled.')
    return redirect('orders:checkout')


# Dashboard views
@login_required
def dashboard_payment_list(request):
    """
    Admin view for payments
    """
    if request.user.user_type != 'Admin':
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')
    
    payments = Payment.objects.select_related('order', 'user').order_by('-payment_date')
    
    # Apply filters
    status = request.GET.get('status')
    if status:
        payments = payments.filter(status=status)
    
    gateway = request.GET.get('gateway')
    if gateway:
        payments = payments.filter(gateway=gateway)
    
    date_from = request.GET.get('date_from')
    if date_from:
        payments = payments.filter(payment_date__date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        payments = payments.filter(payment_date__date__lte=date_to)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(payments, 20)
    page = request.GET.get('page')
    payments = paginator.get_page(page)
    
    # Statistics
    total_volume = payments.aggregate(total=models.Sum('amount'))['total'] or 0
    total_fees = payments.aggregate(total=models.Sum('gateway_fee'))['total'] or 0
    
    context = {
        'payments': payments,
        'total_volume': total_volume,
        'total_fees': total_fees,
        'net_volume': total_volume - total_fees,
    }
    return render(request, 'payments/dashboard/payment_list.html', context)


@method_decorator(login_required, name='dispatch')
class PaymentView(View):
    """
    Step 2: Redirect to PesaPal payment
    """

    def get(self, request, order_id):
        order = get_object_or_404(Order.objects.select_related("event", "user"), id=order_id, user=request.user)

        if order.status == Order.OrderStatus.PAID:
            messages.info(request, "This order has already been paid.")
            return redirect("booking_confirmation", order_id=order.id)

        if order.is_expired:
            with transaction.atomic():
                order.status = Order.OrderStatus.EXPIRED
                order.save()
            messages.error(request, "Order expired. Please book again.")
            return redirect("event-detail", pk=order.event.id)

        try:
            # Register IPN if none exists
            ipn_list = pesapal.get_ipn_list()
            if ipn_list and len(ipn_list) > 0:
                ipn_id = ipn_list[0]["ipn_id"]
            else:
                ipn_id = pesapal.register_ipn(settings.PESAPAL_IPN_URL)["ipn_id"]

            response = pesapal.submit_order(
                order=order,
                callback_url=request.build_absolute_uri(reverse("payments:payment_callback")),
                ipn_id=ipn_id,
            )

            # Save payment record
            Payment.objects.update_or_create(
                order=order,
                defaults={
                    "user": request.user,
                    "transaction_id": response.get("order_tracking_id"),
                    "status": Payment.PaymentStatus.PENDING,
                    "amount": order.total_amount,
                },
            )

            request.session["pesapal_tracking_id"] = response.get("order_tracking_id")
            request.session["payment_order_id"] = order.id

            return render(request, "payments/payments.html", {"order": order, "iframe_url": response["redirect_url"]})

        except Exception as e:
            messages.error(request, f"Payment initialization failed: {str(e)}")
            return redirect("event-detail", pk=order.event.id)
    
    # def get(self, request, order_id):
    #     # Get order
    #     order = get_object_or_404(
    #         Order.objects.select_related('event', 'user'),
    #         id=order_id,
    #         user=request.user
    #     )
        
    #     # Check if order is already paid
    #     if order.status == Order.OrderStatus.PAID:
    #         messages.info(request, "This order has already been paid.")
    #         return redirect('booking_confirmation', order_id=order.id)
        
    #     # Check if order is expired
    #     if order.is_expired:
    #         with transaction.atomic():
    #             order.status = Order.OrderStatus.EXPIRED
    #             order.save()
    #             # Release stock reservation
    #             self.release_stock_reservation(request, order)
    #         messages.error(request, "This order has expired. Please book again.")
    #         return redirect('event_detail', event_id=order.event.id)
        
    #     # Check if order is already processing payment
    #     if hasattr(order, 'payment') and order.payment.status == Payment.PaymentStatus.PENDING:
    #         # Check if we have a tracking ID in session
    #         pesapal_tracking_id = request.session.get('pesapal_tracking_id')
    #         if pesapal_tracking_id:
    #             # Check status with PesaPal
    #             return redirect('payments:payment_status_check', order_id=order.id)
        
    #     try:
    #         # Get fresh token
    #         pesapal.get_access_token(force_refresh=True)
            
    #         # Get or register IPN
    #         ipn_list = pesapal.get_ipn_list()
    #         if ipn_list and len(ipn_list) > 0:
    #             ipn_id = ipn_list[0]['ipn_id']
    #             logger.info(f"Using existing IPN: {ipn_id}")
    #         else:
    #             # Register new IPN
    #             ipn_response = pesapal.register_ipn(settings.PESAPAL_IPN_URL)
    #             ipn_id = ipn_response['ipn_id']
    #             logger.info(f"Registered new IPN: {ipn_id}")
            
    #         # Submit order to PesaPal
    #         response = pesapal.submit_order(
    #             order=order,
    #             callback_url=request.build_absolute_uri(reverse('payments:payment_callback')),
    #             ipn_id=ipn_id,
    #         )
            
    #         logger.info(f"PesaPal response: {response}")
            
    #         if not response.get('redirect_url'):
    #             raise ValueError("No redirect URL from PesaPal")
            
    #         # Create or update payment record
    #         payment, created = Payment.objects.update_or_create(
    #             order=order,
    #             defaults={
    #                 'user': request.user,
    #                 'transaction_id': response.get('order_tracking_id', ''),
    #                 'gateway': Payment.PaymentGateway.PAYPAL,  # PesaPal is similar to PayPal
    #                 'status': Payment.PaymentStatus.PENDING,
    #                 'amount': order.total_amount,
    #                 'payment_method': Order.PaymentMethod.PAYPAL,
    #                 'gateway_response': response
    #             }
    #         )
            
    #         # Store payment tracking info in session
    #         request.session['pesapal_tracking_id'] = response.get('order_tracking_id')
    #         request.session['payment_order_id'] = order.id
    #         request.session['payment_merchant_reference'] = response.get('merchant_reference')
            
    #         return render(request, 'payments/payments.html', {
    #             'order': order,
    #             'iframe_url': response['redirect_url'],
    #             'tracking_id': response.get('order_tracking_id')
    #         })
            
    #     except Order.DoesNotExist:
    #         messages.error(request, "Order not found.")
    #         return redirect('event-list')
    #     except Exception as e:
    #         logger.error(f"Payment initialization error for order {order.id}: {str(e)}", exc_info=True)
    #         return render(request, 'payments/payment_failed.html', {
    #             'error': "Payment initialization failed. Please try again.",
    #             'debug': str(e) if settings.DEBUG else None,
    #             'order': order
    #         })
    
    def release_stock_reservation(self, request, order):
        """Release reserved stock when order expires/cancels"""
        # Clear from session
        if 'reservations' in request.session:
            if str(order.id) in request.session['reservations']:
                del request.session['reservations'][str(order.id)]
                request.session.modified = True
                logger.info(f"Released stock reservation for expired order {order.id}")


@method_decorator(csrf_exempt, name='dispatch')
class PaymentCallbackView(View):
    """
    Step 3: PesaPal callback - Handles payment success/failure
    This is called when user returns from PesaPal
    """
    
    def get(self, request):
        tracking_id = request.GET.get("OrderTrackingId")
        merchant_ref = request.GET.get("OrderMerchantReference")

        if not tracking_id or not merchant_ref:
            messages.error(request, "Invalid payment callback.")
            return redirect("event-list")

        # Verify payment
        status_response = pesapal.check_payment_status(tracking_id)
        payment_status = status_response.get("payment_status_description", "").upper()

        order = get_object_or_404(Order, id=merchant_ref)

        if payment_status == "COMPLETED":
            return self.handle_success(request, order, tracking_id)
        elif payment_status == "FAILED":
            return self.handle_failed(request, order)
        else:
            return redirect("payments:payment_status_check", order_id=order.id)
    
    @transaction.atomic
    def handle_successful_payment(self, request, order, order_tracking_id):
        """Handle successful payment - CREATE TICKETS"""
        
        # Double-check order isn't already processed
        if order.status == Order.OrderStatus.PAID:
            messages.info(request, "Order already processed.")
            return redirect('booking_confirmation', order_id=order.id)
        
        # Update or create payment record
        payment, created = Payment.objects.update_or_create(
            order=order,
            defaults={
                'user': order.user,
                'transaction_id': order_tracking_id,
                'gateway': Payment.PaymentGateway.PAYPAL,
                'status': Payment.PaymentStatus.COMPLETED,
                'amount': order.total_amount,
                'payment_method': Order.PaymentMethod.PAYPAL,
                'payment_date': timezone.now()
            }
        )
        
        # CREATE TICKETS - one for each quantity
        order_items = order.order_items.all()
        
        for order_item in order_items:
            ticket_type = order_item.ticket_type
            
            for i in range(order_item.quantity):
                # Generate unique ticket number
                ticket_number = f"TKT-{uuid.uuid4().hex[:10].upper()}"
                
                ticket = Ticket.objects.create(
                    order=order,
                    order_item=order_item,
                    ticket_type=ticket_type,
                    event=order.event,
                    attendee_name=order.user.get_full_name() or order.user.username,
                    attendee_email=order.user.email,
                    attendee_phone=order.phone_number,
                    status=Ticket.TicketStatus.VALID,
                    ticket_number=ticket_number
                )
                
                # Generate QR code
                ticket.generate_qr_code()
                ticket.save()
                
                logger.info(f"Created ticket {ticket.ticket_number} for order {order.id}")
        
        # Update order status
        order.status = Order.OrderStatus.PAID
        order.payment_date = timezone.now()
        order.save()
        
        # Clear stock reservation from session
        self.clear_session_reservation(request, order)
        
        # Send confirmation email (implement this)
        self.send_confirmation_email(order)
        
        messages.success(request, "Payment successful! Your tickets are ready.")
        
        # Clear session data
        if 'pesapal_tracking_id' in request.session:
            del request.session['pesapal_tracking_id']
        if 'payment_order_id' in request.session:
            del request.session['payment_order_id']
        
        return redirect('booking_confirmation', order_id=order.id)
    
    @transaction.atomic
    def handle_failed_payment(self, request, order):
        """Handle failed payment - RESTORE STOCK, NO TICKETS CREATED"""
        
        # Update order status
        order.status = Order.OrderStatus.FAILED
        order.save()
        
        # Update payment record if exists
        if hasattr(order, 'payment'):
            order.payment.status = Payment.PaymentStatus.FAILED
            order.payment.save()
        
        # Clear stock reservation
        self.clear_session_reservation(request, order)
        
        messages.warning(request, "Payment failed. You can try again or choose another payment method.")
        
        return redirect('event-detail', event_id=order.event.id)
    
    def clear_session_reservation(self, request, order):
        """Clear stock reservation from session"""
        if 'reservations' in request.session:
            if str(order.id) in request.session['reservations']:
                del request.session['reservations'][str(order.id)]
                request.session.modified = True
                logger.info(f"Cleared reservation for order {order.id}")
    
    def send_confirmation_email(self, order):
        """Send confirmation email with tickets"""
        # Implement email sending here
        # You can use Django's send_mail or a service like SendGrid
        logger.info(f"Confirmation email would be sent for order {order.id}")

class PaymentFailedView(View):
    def get(self, request, order_id):
        """
        Display payment failed page for a specific order.
        """
        # Get the order or return 404
        order = get_object_or_404(Order, id=order_id)
        
        # Ensure this order belongs to the current user
        if order.user != request.user:
            return render(request, 'payment_error.html', {
                'error': "You don't have permission to view this order"
            })
        
        # Mark all tickets in this order as failed
        tickets = order.tickets.all()  # assuming Ticket has ForeignKey to Order as 'order'
        for ticket in tickets:
            if ticket.status != 'Failed':
                ticket.status = 'Failed'
                ticket.save()
        
        # Render the failed payment template
        return render(request, 'payment_failed.html', {
            'order': order,
            'tickets': tickets,
            'error_message': "Your payment was not successful. Please try again."
        })

@method_decorator(csrf_exempt, name='dispatch')
class PaymentIPNView(View):
    """
    PesaPal IPN (Instant Payment Notification) endpoint
    This is called by PesaPal server-to-server to confirm payment status
    """
    
    def get(self, request):
        """PesaPal sends IPN via GET"""
        return self.process_ipn(request)
    
    def post(self, request):
        """Handle POST if PesaPal sends that way"""
        return self.process_ipn(request)
    
    def process_ipn(self, request):
        """
        Process IPN notification from PesaPal
        This is server-to-server, no user session
        """
        # Get parameters
        order_tracking_id = request.GET.get('OrderTrackingId') or request.POST.get('OrderTrackingId')
        order_merchant_reference = request.GET.get('OrderMerchantReference') or request.POST.get('OrderMerchantReference')
        
        logger.info(f"IPN received: Tracking ID: {order_tracking_id}, Reference: {order_merchant_reference}")
        
        if not order_tracking_id or not order_merchant_reference:
            logger.error("Missing required parameters in IPN")
            return HttpResponse("Missing parameters", status=400)
        
        # Verify with PesaPal
        try:
            pesapal.get_access_token()
            status_response = pesapal.check_payment_status(order_tracking_id)
            
            payment_status = status_response.get('payment_status_description', '').upper()
            logger.info(f"IPN payment status: {payment_status}")
            
        except Exception as e:
            logger.error(f"Failed to verify IPN payment status: {str(e)}")
            return HttpResponse("Verification failed", status=500)
        
        # Find the order
        try:
            order = Order.objects.select_for_update().get(id=order_merchant_reference)
        except Order.DoesNotExist:
            logger.error(f"Order not found for IPN: {order_merchant_reference}")
            return HttpResponse("Order not found", status=404)
        
        # Process based on status
        if payment_status == 'COMPLETED' and order.status != Order.OrderStatus.PAID:
            self.process_successful_payment(order, order_tracking_id)
        elif payment_status == 'FAILED' and order.status != Order.OrderStatus.FAILED:
            self.process_failed_payment(order)
        
        # Return success to PesaPal
        return HttpResponse("IPN processed successfully", status=200)
    
    @transaction.atomic
    def process_successful_payment(self, order, order_tracking_id):
        """Process successful payment from IPN"""
        
        # Create payment record if not exists
        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                'user': order.user,
                'transaction_id': order_tracking_id,
                'gateway': Payment.PaymentGateway.PAYPAL,
                'status': Payment.PaymentStatus.COMPLETED,
                'amount': order.total_amount,
                'payment_method': Order.PaymentMethod.PAYPAL,
                'payment_date': timezone.now()
            }
        )
        
        if not created and payment.status != Payment.PaymentStatus.COMPLETED:
            payment.status = Payment.PaymentStatus.COMPLETED
            payment.transaction_id = order_tracking_id
            payment.payment_date = timezone.now()
            payment.save()
        
        # CREATE TICKETS if they don't exist
        if not order.tickets.exists():
            order_items = order.order_items.all()
            
            for order_item in order_items:
                ticket_type = order_item.ticket_type
                
                for i in range(order_item.quantity):
                    ticket_number = f"TKT-{uuid.uuid4().hex[:10].upper()}"
                    
                    ticket = Ticket.objects.create(
                        order=order,
                        order_item=order_item,
                        ticket_type=ticket_type,
                        event=order.event,
                        attendee_name=order.user.get_full_name() or order.user.username,
                        attendee_email=order.user.email,
                        attendee_phone=order.phone_number,
                        status=Ticket.TicketStatus.VALID,
                        ticket_number=ticket_number
                    )
                    ticket.generate_qr_code()
                    ticket.save()
            
            logger.info(f"Created tickets via IPN for order {order.id}")
        
        # Update order status
        if order.status != Order.OrderStatus.PAID:
            order.status = Order.OrderStatus.PAID
            order.payment_date = timezone.now()
            order.save()
        
        logger.info(f"IPN processed successful payment for order {order.id}")
    
    @transaction.atomic
    def process_failed_payment(self, order):
        """Process failed payment from IPN"""
        
        # Update payment if exists
        if hasattr(order, 'payment'):
            order.payment.status = Payment.PaymentStatus.FAILED
            order.payment.save()
        
        # Update order status
        if order.status != Order.OrderStatus.FAILED:
            order.status = Order.OrderStatus.FAILED
            order.save()
        
        logger.info(f"IPN processed failed payment for order {order.id}")


@login_required
def payment_status_check(request, order_id):
    """
    Check payment status for an order
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Get tracking ID from session or payment record
    tracking_id = request.session.get('pesapal_tracking_id')
    
    if not tracking_id and hasattr(order, 'payment'):
        tracking_id = order.payment.transaction_id
    
    if not tracking_id:
        messages.error(request, "No payment tracking information found.")
        return redirect('payment_page', order_id=order.id)
    
    try:
        pesapal.get_access_token()
        status_response = pesapal.check_payment_status(tracking_id)
        
        payment_status = status_response.get('payment_status_description', '').upper()
        
        if payment_status == 'COMPLETED':
            # If payment completed but order not updated
            if order.status != Order.OrderStatus.PAID:
                # Process as successful
                from django.shortcuts import redirect
                callback_view = PaymentCallbackView()
                return callback_view.handle_successful_payment(request, order, tracking_id)
            else:
                return redirect('booking_confirmation', order_id=order.id)
        elif payment_status == 'FAILED':
            return redirect('payment_page', order_id=order.id)
        else:
            # Still pending
            context = {
                'order': order,
                'tracking_id': tracking_id,
                'status': payment_status,
                'status_response': status_response
            }
            return render(request, 'payments/payment_pending.html', context)
            
    except Exception as e:
        logger.error(f"Payment status check failed: {str(e)}")
        messages.error(request, "Failed to check payment status. Please try again.")
        return redirect('payment_page', order_id=order.id)
    


@login_required
def payment_retry(request, order_id):
    """
    Retry payment for a failed order
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status != Order.OrderStatus.FAILED:
        messages.info(request, "This order cannot be retried.")
        return redirect('order_detail', order_id=order.id)
    
    # Reset order to pending
    order.status = Order.OrderStatus.PENDING
    order.expiry_date = timezone.now() + timezone.timedelta(minutes=30)
    order.save()
    
    messages.success(request, "You can now retry payment.")
    return redirect('payment_page', order_id=order.id)

# class PaymentView(View):
#     def get(self, request, order_id):  # Add order_id parameter
#         # Get order from session or directly from URL
#         order_id = order_id or request.session.get('current_order_id')
#         if not order_id:
#             messages.error(request, "No order found. Please start over.")
#             return redirect('event-list')
            
#         try:
#             order = Order.objects.select_related('event').get(
#                 id=order_id,
#                 user = request.user
#                 )
            
#             # Make sure the order belongs to this user
#             if order.user != request.user:
#                 messages.error(request, "You don't have permission to access this order.")
#                 return redirect('event-list')
            
#             # Get fresh token first
#             pesapal.get_access_token(force_refresh=True)
            
#             ipn_list = pesapal.get_ipn_list()
#             ipn_id = ipn_list[0]['ipn_id'] if ipn_list else pesapal.register_ipn(settings.PESAPAL_IPN_URL)['ipn_id']
            
#             response = pesapal.submit_order(
#                 order=order,  # Pass the order object
#                 callback_url=request.build_absolute_uri(settings.PESAPAL_CALLBACK_URL),
#                 ipn_id=ipn_id,
#             )
            
#             if not response.get('redirect_url'):
#                 raise ValueError("No redirect URL from PesaPal")
                
#             return render(request, 'payments/payments.html', {
#                 'order': order,
#                 'iframe_url': response['redirect_url']
#             })
#         except Order.DoesNotExist:
#             messages.error(request, "Order not found.")
#             return redirect('event-list')
#         except Exception as e:
#             print(f"Payment Error: {str(e)}")
#             return render(request, 'payments/payment_failed.html', {
#                 'error': "Payment initialization failed",
#                 'debug': str(e)
#             })

