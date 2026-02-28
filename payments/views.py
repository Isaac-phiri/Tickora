# from django.shortcuts import render
# from django.http import JsonResponse
# from tickets.models import Ticket
# from django.core.mail import send_mail
# from django.conf import settings
# from django.core.mail import send_mail
# from django.template.loader import render_to_string
# from django.conf import settings
# from django.utils.html import strip_tags
# import requests

# # views.py
# from django.urls import reverse_lazy
# from django.db.models import Count
# from events.models import Event
# from django.shortcuts import get_object_or_404, redirect, render
# from django.contrib.auth.decorators import login_required
# from opera.models import Order
# from django.urls import reverse
# from accounts.models import User
# # payments/views.py
# from django.shortcuts import render, redirect, get_object_or_404
# from django.views.decorators.csrf import csrf_exempt
# from django.http import JsonResponse, HttpResponse
# from django.conf import settings
# from .pasapal_service import PesaPalService
# from django.template.loader import render_to_string
# from django.core.mail import send_mail
# from django.views import View

# from tickets.views import send_ticket_email
# pesapal = PesaPalService()

# class PaymentView(View):
#     def get(self, request):
#         ticket_id = request.session.get('current_ticket_id')
#         if not ticket_id:
#             return redirect('some_error_page')
            
#         try:
#             ticket = Ticket.objects.get(ticket_id=ticket_id)
            
#             # Get fresh token first
#             pesapal.get_access_token(force_refresh=True)
            
#             ipn_list = pesapal.get_ipn_list()
#             ipn_id = ipn_list[0]['ipn_id'] if ipn_list else pesapal.register_ipn(settings.PESAPAL_IPN_URL)['ipn_id']
            
#             response = pesapal.submit_order(
#                 ticket=ticket,
#                 callback_url=request.build_absolute_uri(settings.PESAPAL_CALLBACK_URL),
#                 ipn_id=ipn_id,
#             )
            
#             if not response.get('redirect_url'):
#                 raise ValueError("No redirect URL from PesaPal")
                
#             return render(request, 'payments/payments.html', {
#                 'order': ticket,
#                 'iframe_url': response['redirect_url']
#             })
            
#         except Exception as e:
#             print(f"Payment Error: {str(e)}")
#             return render(request, 'payments/payment_failed.html', {
#                 'error': "Payment initialization failed",
#                 'debug': str(e)
#             })

# class PaymentFailedView(View):
#     def get(self, request, ticket_id):
#         # Get the ticket or return 404
#         ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
        
#         # Ensure this ticket belongs to the current user
#         if ticket.user != request.user:
#             return render(request, 'payment_error.html', {
#                 'error': "You don't have permission to view this ticket"
#             })
        
#         # Update payment status if not already failed
#         if ticket.payment_status != 'Failed':
#             ticket.payment_status = 'Failed'
#             ticket.save()
        
#         # Get the event for displaying details
#         event = ticket.event
        
#         # Render the failed payment template
#         return render(request, 'payment_failed.html', {
#             'ticket': ticket,
#             'event': event,
#             'error_message': "Your payment was not successful. Please try again."
#         })
# import logging

# logger = logging.getLogger(__name__)
# @csrf_exempt
# def payment_callback(request):
#     logger.info("\n=== PesaPal Callback Received ===")
#     logger.info("GET Parameters: %s", request.GET)
#     logger.info("POST Data: %s", request.POST)
    
#     # For IPN notifications (POST requests)
#     if request.method == 'POST':
#         try:
#             # Get the order tracking ID from PesaPal
#             order_tracking_id = request.POST.get('order_tracking_id')
#             if not order_tracking_id:
#                 return HttpResponse("Missing order_tracking_id", status=400)
                
#             # Verify the payment status with PesaPal
#             pesapal.get_access_token(force_refresh=True)
#             status_response = pesapal.get_payment_status(order_tracking_id)
            
#             if status_response.get('payment_status') == 'COMPLETED':
#                 # Find the ticket (assuming order_tracking_id is your ticket_id)
#                 try:
#                     ticket = Ticket.objects.get(ticket_id=order_tracking_id)
#                     if ticket.payment_status != 'Paid':
#                         ticket.payment_status = 'Paid'
#                         ticket.save()
                        
#                         # Send ticket to user
#                         send_ticket_email(ticket)
                        
#                 except Ticket.DoesNotExist:
#                     logger.error("Ticket not found for order_tracking_id: %s", order_tracking_id)
            
#             return HttpResponse("IPN processed", status=200)
            
#         except Exception as e:
#             logger.error("Error processing IPN: %s", str(e))
#             return HttpResponse("Error processing IPN", status=500)
    
#     # For browser redirects (GET requests)
#     return HttpResponse("Callback received", status=200)

# def payment_success(request):
#     # Retrieve ticket_id from URL or session
#     ticket_id = request.GET.get("ticket_id") or request.session.get('current_ticket_id')
#     if not ticket_id:
#         return render(request, 'payments/error.html', {'message': "Invalid payment URL"})

#     # Get the ticket from the database
#     ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
    
#     # Double-check payment status with PesaPal API
#     try:
#         pesapal.get_access_token(force_refresh=True)
#         status_response = pesapal.get_payment_status(ticket.ticket_id)
        
#         if status_response.get('payment_status') == 'COMPLETED' and ticket.payment_status != 'Paid':
#             ticket.payment_status = "Paid"
#             ticket.save()
#             send_ticket_email(ticket)
#     except Exception as e:
#         logger.error(f"Error verifying payment status: {str(e)}")
#         # You might want to handle this case differently
    
#     return render(request, 'payments/success.html', {'ticket': ticket})

# @csrf_exempt
# def payment_ipn(request):
#     """Instant Payment Notification (IPN) endpoint"""
#     if request.method == 'GET':
#         order_tracking_id = request.GET.get('OrderTrackingId')
#         order_merchant_reference = request.GET.get('OrderMerchantReference')
        
#         if order_tracking_id and order_merchant_reference:
#             try:
#                 ticket = Ticket.objects.get(ticket_id=order_merchant_reference)
#                 status_response = pesapal.check_payment_status(order_tracking_id)
#                 payment_status = status_response.get('payment_status')
                
#                 if payment_status == 'COMPLETED' and ticket.payment_status != 'Paid':
#                     ticket.payment_status = 'Paid'
#                     ticket.save()
#                     # You might want to send a confirmation email here
                
#                 return HttpResponse(status=200)
            
#             except Exception as e:
#                 print(f"IPN processing failed: {str(e)}")
#                 return HttpResponse(status=400)
    
#     return HttpResponse(status=400)




# # PESAPAL_ENV = "sandbox"  # Change to 'sandbox' for testing
# # PESAPAL_URLS = {
# #     "sandbox": "https://cybqa.pesapal.com/pesapalv3/api/",
# #     "live": "https://pay.pesapal.com/v3/api/",
# # }
# # BASE_URL = PESAPAL_URLS[PESAPAL_ENV]


# # def get_access_token():
# #     url = BASE_URL + "Auth/RequestToken"
# #     headers = {"Accept": "application/json", "Content-Type": "application/json"}
# #     data = {"consumer_key": settings.CONSUMER_KEY, "consumer_secret": settings.CONSUMER_SECRET}
# #     response = requests.post(url, json=data, headers=headers)
# #     response_data = response.json()
# #     return response_data.get("token")


# # def register_ipn(token):
# #     url = BASE_URL + "URLSetup/RegisterIPN"
# #     headers = {
# #         "Accept": "application/json",
# #         "Content-Type": "application/json",
# #         "Authorization": f"Bearer {token}"
# #     }
# #     data = {"url": "http://127.0.0.1:8000/pesapal/ipn/", "ipn_notification_type": "POST"}
    
# #     response = requests.post(url, json=data, headers=headers)
    
# #     if response.status_code == 200:
# #         return response.json().get("ipn_id")
# #     else:
# #         return None  # Explicitly returning None if registration fails

# # def payments(request, ticket_id):
# #     ticket = get_object_or_404(Ticket, id=ticket_id)
# #     token = get_access_token()
    
# #     if not token:
# #         return JsonResponse({"error": "Failed to retrieve access token"}, status=400)
    
# #     ipn_id = register_ipn(token)
# #     if not ipn_id:
# #         return JsonResponse({"error": "Failed to register IPN"}, status=400)
    
# #     url = BASE_URL + "Transactions/SubmitOrderRequest"
# #     headers = {
# #         "Accept": "application/json",
# #         "Content-Type": "application/json",
# #         "Authorization": f"Bearer {token}"
# #     }
# #     data = {
# #         "id": str(ticket.id),
# #         "currency": "KES",
# #         "amount": float(ticket.total_price),
# #         "description": f"Payment for {ticket.quantity} x {ticket.ticket_type} - {ticket.event.event_name}",
# #         "callback_url": request.build_absolute_uri('/payments/success/'),
# #         "notification_id": ipn_id,
# #         "billing_address": {
# #             "email_address": request.user.email,
# #             "phone_number": request.user.profile.phone_number,
# #             "country_code": "KE",
# #             "first_name": request.user.first_name,
# #             "last_name": request.user.last_name,
# #             "line_1": "Your Company",
# #             "city": "",
# #             "state": "",
# #             "postal_code": "",
# #             "zip_code": ""
# #         }
# #     }
# #     response = requests.post(url, json=data, headers=headers)
    
# #     if response.status_code == 200:
# #         response_data = response.json()
# #         return redirect(response_data.get("redirect_url"))
    
# #     return JsonResponse({"error": "Failed to initiate payment."}, status=400)





# # def initiate_payment(request, ticket_id):
# #     ticket = get_object_or_404(Ticket, ticket_id=ticket_id, user=request.user)
    
# #     if ticket.payment_status == 'Paid':
# #         return render(request, 'payment_already_paid.html', {'ticket': ticket})
    
# #     try:
# #         # Register IPN if not already done (you might want to do this separately)
# #         ipn_list = pesapal.get_ipn_list()
# #         if not ipn_list:
# #             ipn_response = pesapal.register_ipn(settings.PESAPAL_IPN_URL)
# #             ipn_id = ipn_response.get('ipn_id')
# #         else:
# #             ipn_id = ipn_list[0].get('ipn_id')  # Using the first registered IPN
        
# #         # Submit order
# #         response = pesapal.submit_order(
# #             ticket=ticket,
# #             callback_url=request.build_absolute_uri(settings.PESAPAL_CALLBACK_URL),
# #             ipn_id=ipn_id
# #         )
        
# #         # Redirect to PesaPal payment page
# #         return redirect(response.get('payments'))
    
# #     except Exception as e:
# #         # Log the error
# #         print(f"Payment initiation failed: {str(e)}")
# #         return render(request, 'payment_error.html', {'error': str(e)})
    






# # def payments(request, ticket_id):
# #     ticket = get_object_or_404(Ticket, id=ticket_id)

# #     if request.method == 'POST':
# #         try:
# #             # Create a Stripe Checkout Session
# #             checkout_session = stripe.checkout.Session.create(
# #                 payment_method_types=['card'],
# #                 line_items=[{
# #                     'price_data': {
# #                         'currency': 'usd',
# #                         'product_data': {
# #                             'name': f"{ticket.quantity} x {ticket.ticket_type} - {ticket.event.event_name}",
# #                         },
# #                         'unit_amount': int(ticket.total_price * 100),  # Convert to cents
# #                     },
# #                     'quantity': 1,
# #                 }],
# #                 mode='payment',
# #                 success_url=request.build_absolute_uri('/payments/success/') + f"?ticket_id={ticket.id}",
# #                 cancel_url=request.build_absolute_uri('/payments/cancel/'),
# #             )

# #             return redirect(checkout_session.url, code=303)

# #         except Exception as e:
# #             return JsonResponse({'error': str(e)})

# #     return render(request, 'payments/payments.html', {'order': ticket, 'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY})



# # def payment_success(request):
# #     # Retrieve ticket_id from URL
# #     ticket_id = request.GET.get("ticket_id")
# #     if not ticket_id:
# #         return render(request, 'payments/error.html', {'message': "Invalid payment URL"})

# #     # Get the ticket from the database
# #     ticket = get_object_or_404(Ticket, id=ticket_id)
    
# #     # Update payment status
# #     ticket.payment_status = "Paid"
# #     ticket.save()

# #     # Send email with ticket details
# #     subject = f"Your Ticket for {ticket.event.event_name}"
# #     recipient_email = ticket.user.email

# #     email_html_content = render_to_string('emails/ticket_email.html', {'ticket': ticket})
# #     email_plain_text = strip_tags(email_html_content)

# #     send_mail(
# #         subject,
# #         email_plain_text,
# #         settings.DEFAULT_FROM_EMAIL,
# #         [recipient_email],
# #         html_message=email_html_content,
# #         fail_silently=False,
# #     )

# #     return render(request, 'payments/success.html', {'ticket': ticket})

# def payment_cancel(request):
#     return render(request, 'payments/cancel.html')








# # def make_payments(request, ticket_id):
    
# #     ticket = get_object_or_404(Ticket, id=ticket_id)

# #     if request.method == 'POST':
# #         # Here you would integrate with a payment gateway (e.g., Stripe, PayPal)
# #         # For simplicity, we assume the payment is successful.

# #         # On successful payment
# #         ticket.sales_status = 'Sold Out'
# #         ticket.save()

# #         # Redirect to payment success page
# #         return redirect('payment_success', ticket_id=ticket.id)

# #     return render(request, 'payments/payments.html', {'ticket': ticket})





# def make_payment(request):
#     if request.method == 'POST':
#         amount = request.POST.get('amount')
#         phone_number = request.POST.get('number')
#         reference = request.POST.get('reference')

#         if not all([amount, phone_number, reference]):
#             return JsonResponse({"message": "Please provide all required inputs (amount, number, and reference)"}, status=400)

#         airtel = AirtelMoneyService()
#         access_token = airtel.get_auth_token()

#         if not access_token:
#             return JsonResponse({"message": "Failed to retrieve access token"}, status=500)

#         result = airtel.make_collection_payment(access_token, reference, phone_number, amount)
#         return JsonResponse(result)

#     return render(request, 'payments/make_payment.html')

# def check_transaction_status(request, transaction_id):
#     airtel = AirtelMoneyService()
#     access_token = airtel.get_auth_token()

#     if not access_token:
#         return JsonResponse({"message": "Failed to retrieve access token"}, status=500)

#     result = airtel.check_collection_status(access_token, transaction_id)
#     return JsonResponse(result)

# from django.core.mail import send_mail

# # def payment_success(request, ticket_id):
# #     ticket = get_object_or_404(Ticket, id=ticket_id)

# #     # Send ticket to the user's email
# #     send_mail(
# #         'Your Ticket for ' + ticket.event.event_name,
# #         f'Thank you for purchasing a ticket. Here are your details:\n'
# #         f'Ticket Type: {ticket.ticket_type}\n'
# #         f'Event: {ticket.event.event_name}\n'
# #         f'Total Price: {ticket.total_price}\n',
# #         settings.DEFAULT_FROM_EMAIL,
# #         [ticket.user.email],
# #         fail_silently=False,
# #     )

# #     return render(request, 'payments/payment_status.html', {'ticket': ticket})


