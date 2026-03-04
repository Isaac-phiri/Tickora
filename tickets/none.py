from django.http import HttpResponse
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
import random
import string
import uuid
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
import base64

from events.models import Event
from tickets.models import TicketType, Ticket
from orders.models import Order, OrderItem
from payments.models import Payment



class EventBookingView(View):
    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        
        # Get available ticket types for this event
        ticket_types = TicketType.objects.filter(
            event=event,
            is_active=True,
            sales_start_date__lte=timezone.now(),
            sales_end_date__gte=timezone.now()
        ).order_by('price')
        
        context = {
            'event': event,
            'ticket_types': ticket_types,
            'now': timezone.now(),
        }
        return render(request, 'event/event_detail.html', context)

    @transaction.atomic
    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        
        # Get form data
        ticket_type_id = request.POST.get('ticket_type')
        quantity = int(request.POST.get('quantity', 1))
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        
        # Validate ticket type
        ticket_type = get_object_or_404(TicketType, id=ticket_type_id, event=event)
        
        # Validate quantity
        if quantity < ticket_type.min_per_order:
            messages.error(request, f"Minimum {ticket_type.min_per_order} ticket(s) per order.")
            return redirect('event_detail', event_id=event.id)
        
        if quantity > ticket_type.max_per_order:
            messages.error(request, f"Maximum {ticket_type.max_per_order} ticket(s) per order.")
            return redirect('event_detail', event_id=event.id)
        
        if quantity > ticket_type.tickets_remaining:
            messages.error(request, f"Only {ticket_type.tickets_remaining} tickets available.")
            return redirect('event_detail', event_id=event.id)
        
        # Handle user authentication/creation
        if not request.user.is_authenticated:
            # Check if user with this email already exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Generate a random password
                password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                
                # Split full name into first and last names
                name_parts = full_name.split(' ')
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                
                # Create username from email
                username = email.split('@')[0]
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                # Create the user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password
                )
                
                # You might want to create a user profile for phone number
                # if you have a Profile model
                
                # Automatically log in the new user
                login(request, user)
                
                # Here you would send welcome email with password
                # send_welcome_email(user.email, password)
        else:
            user = request.user
        
        # Calculate totals
        unit_price = ticket_type.current_price
        subtotal = unit_price * quantity
        service_fee = (subtotal * ticket_type.service_fee_percentage / 100) + ticket_type.service_fee_fixed
        total_amount = subtotal + service_fee
        
        # Create Order
        order = Order.objects.create(
            user=user,
            email=email if not request.user.is_authenticated else user.email,
            phone_number=phone_number,
            event=event,
            status=Order.OrderStatus.PENDING,
            subtotal=subtotal,
            service_fee_total=service_fee,
            total_amount=total_amount,
            expiry_date=timezone.now() + timezone.timedelta(minutes=30)
        )
        
        # Create OrderItem
        order_item = OrderItem.objects.create(
            order=order,
            ticket_type=ticket_type,
            quantity=quantity,
            unit_price=unit_price,
            service_fee=service_fee,
            subtotal=subtotal
        )
        

        # Create individual tickets
        tickets = []
        for i in range(quantity):
            ticket = Ticket.objects.create(
                order=order,
                order_item=order_item,
                ticket_type=ticket_type,
                event=event,
                attendee_name=user.full_name,
                attendee_email=user.email,
                attendee_phone=user.phone_number,
                status=Ticket.TicketStatus.VALID
            )
            tickets.append(ticket)
        
        # Store order info in session
        request.session['current_order_id'] = order.id
        
        messages.success(request, f"Booking created! Please complete payment for {quantity} ticket(s).")
        
        # Redirect to payment page
        return redirect('payments:payment_page', order_id=order.id)
    


@login_required
def booking_confirmation(request, order_id):
    """
    Display booking confirmation after successful payment
    """
    order = get_object_or_404(
        Order.objects.select_related('event', 'user').prefetch_related(
            'order_items__ticket_type',
            'tickets'
        ),
        id=order_id,
        user=request.user
    )
    
    # Check if payment is completed
    if order.status != Order.OrderStatus.PAID:
        messages.warning(request, "This order hasn't been paid yet.")
        return redirect('payment_page', order_id=order.id)
    
    # Get payment info
    payment = getattr(order, 'payment', None)
    
    # Get all tickets for this order
    tickets = order.tickets.all()
    
    context = {
        'order': order,
        'payment': payment,
        'tickets': tickets,
        'event': order.event,
        'order_items': order.order_items.all(),
    }
    
    return render(request, 'event/booking_confirmation.html', context)