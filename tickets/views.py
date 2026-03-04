from django.http import HttpResponse
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.utils import timezone
from accounts.models import User
import random
import string
import uuid
import logging
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
import base64
import requests
from events.models import Event
from tickets.models import TicketType, Ticket
from orders.models import Order, OrderItem
from payments.models import Payment
logger = logging.getLogger(__name__)


class EventBookingView(View):
    """
    Step 1: User books tickets
    - Creates Order (PENDING)
    - Creates OrderItem
    - Reserves stock (temporarily reduces available quantity)
    - NO tickets created yet
    """
    
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
        ticket_type = get_object_or_404(
            TicketType.objects.select_for_update(),  # Lock row for update
            id=ticket_type_id, 
            event=event
        )
        
        # Validate quantity
        if quantity < ticket_type.min_per_order:
            messages.error(request, f"Minimum {ticket_type.min_per_order} ticket(s) per order.")
            return redirect('event_detail', event_id=event.id)
        
        if quantity > ticket_type.max_per_order:
            messages.error(request, f"Maximum {ticket_type.max_per_order} ticket(s) per order.")
            return redirect('event_detail', event_id=event.id)
        
        # Check availability BEFORE reservation
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
                # username = email.split('@')[0]
                # base_username = username
                # counter = 1
                # while User.objects.filter(username=username).exists():
                #     username = f"{base_username}{counter}"
                #     counter += 1
                
                # Create the user
                user = User.objects.create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password
                )
                
                # Log in the new user
                login(request, user)
                
                # You could send welcome email with password here
                # send_welcome_email(user.email, password)
        else:
            user = request.user
        
        # Calculate totals
        unit_price = ticket_type.current_price
        subtotal = unit_price * quantity
        service_fee = (subtotal * ticket_type.service_fee_percentage / 100) + ticket_type.service_fee_fixed
        total_amount = subtotal + service_fee
        
        # Create Order (PENDING)
        order = Order.objects.create(
            user=user,
            email=email if not request.user.is_authenticated else user.email,
            phone_number=phone_number,
            event=event,
            status=Order.OrderStatus.PENDING,
            subtotal=subtotal,
            service_fee_total=service_fee,
            total_amount=total_amount,
            expiry_date=timezone.now() + timezone.timedelta(minutes=30)  # 30 minutes to complete payment
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
        
        # RESERVE STOCK: Temporarily reduce available quantity
        # We don't create tickets yet, just mark the stock as reserved
        # You might want to add a 'reserved_quantity' field to TicketType
        # For now, we'll use a cache or session-based reservation
        # Alternative: Create temporary reservation records
        self.create_stock_reservation(request, ticket_type, quantity, order)
        
        # Store order info in session
        request.session['current_order_id'] = order.id
        request.session['booking_email'] = email
        request.session['booking_phone'] = phone_number
        
        messages.success(request, f"Booking created! Please complete payment for {quantity} ticket(s).")
        
        # Redirect to payment page
        return redirect('payments:payment_page', order_id=order.id)
    
    def create_stock_reservation(self, request, ticket_type, quantity, order):
        """
        Create a stock reservation.
        You can implement this using:
        1. A Reservation model
        2. Redis cache
        3. Session storage
        4. Or add a 'reserved_quantity' field to TicketType
        """
        # Option 1: Using Redis (recommended for production)
        # cache.set(f"reservation_{order.id}", {
        #     'ticket_type_id': ticket_type.id,
        #     'quantity': quantity,
        #     'expires': timezone.now() + timezone.timedelta(minutes=30)
        # }, timeout=1800)
        
        # Option 2: Using session (simpler for development)
        if 'reservations' not in request.session:
            request.session['reservations'] = {}
        
        request.session['reservations'][str(order.id)] = {
            'ticket_type_id': ticket_type.id,
            'quantity': quantity,
            'expires': (timezone.now() + timezone.timedelta(minutes=30)).isoformat()
        }
        request.session.modified = True
        
        # Option 3: Using a Reservation model (if you have one)
        # Reservation.objects.create(
        #     ticket_type=ticket_type,
        #     order=order,
        #     quantity=quantity,
        #     expires_at=timezone.now() + timezone.timedelta(minutes=30)
        # )


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
    
    # Verify order is paid
    if order.status != Order.OrderStatus.PAID:
        messages.warning(request, "This order hasn't been paid yet.")
        return redirect('payment_page', order_id=order.id)
    
    # Get payment info
    payment = getattr(order, 'payment', None)
    
    # Get all tickets for this order
    tickets = order.tickets.all()
    
    # Check if tickets exist (they should at this point)
    if not tickets.exists():
        logger.error(f"Order {order.id} is PAID but has no tickets!")
        messages.error(request, "There was an error generating your tickets. Please contact support.")
        return redirect('event-list')
    
    context = {
        'order': order,
        'payment': payment,
        'tickets': tickets,
        'event': order.event,
        'order_items': order.order_items.all(),
        'total_tickets': tickets.count(),
    }
    
    return render(request, 'event/booking_confirmation.html', context)

@login_required
def download_ticket(request, ticket_id):
    """
    Download individual ticket as HTML
    """
    ticket = get_object_or_404(
        Ticket.objects.select_related('event', 'ticket_type', 'order__user'),
        id=ticket_id,
        order__user=request.user
    )
    
    # Convert QR code to base64 if it's a file
    qr_code_base64 = None
    if ticket.qr_code:
        try:
            with open(ticket.qr_code.path, 'rb') as f:
                qr_code_base64 = base64.b64encode(f.read()).decode()
        except:
            pass
    
    # Create HTML ticket
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ticket - {ticket.event.title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
            .ticket {{ 
                max-width: 600px; 
                margin: 0 auto; 
                background: white; 
                border-radius: 15px; 
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            }}
            .ticket-header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .ticket-body {{ padding: 30px; }}
            .info-row {{ display: flex; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
            .info-label {{ width: 120px; font-weight: bold; color: #666; }}
            .info-value {{ flex: 1; color: #333; }}
            .qr-section {{ text-align: center; margin: 30px 0; }}
            .qr-section img {{ max-width: 200px; }}
            .ticket-footer {{ 
                background: #f8f9fa;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                color: #666;
                border-top: 1px dashed #ddd;
            }}
        </style>
    </head>
    <body>
        <div class="ticket">
            <div class="ticket-header">
                <h2>{ticket.event.title}</h2>
                <p>Ticket #{ticket.ticket_number}</p>
            </div>
            <div class="ticket-body">
                <div class="info-row">
                    <div class="info-label">Event Date:</div>
                    <div class="info-value">{ticket.event.start_date|date:"l, F d, Y"}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Time:</div>
                    <div class="info-value">{ticket.event.start_date|date:"g:i A"}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Venue:</div>
                    <div class="info-value">{ticket.event.venue_name}<br>{ticket.event.city}, {ticket.event.state}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Attendee:</div>
                    <div class="info-value">{ticket.attendee_name}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Email:</div>
                    <div class="info-value">{ticket.attendee_email}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Ticket Type:</div>
                    <div class="info-value">{ticket.ticket_type.name}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Order #:</div>
                    <div class="info-value">{ticket.order.order_number}</div>
                </div>
    """
    
    if qr_code_base64:
        html += f"""
                <div class="qr-section">
                    <img src="data:image/png;base64,{qr_code_base64}" alt="QR Code">
                    <p style="margin: 5px 0 0; font-size: 12px; color: #666;">Scan at entrance</p>
                </div>
        """
    
    html += """
            </div>
            <div class="ticket-footer">
                <p>This ticket is valid for one person only. Please present this QR code at the entrance.</p>
                <p>For any queries, contact support@example.com</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    response = HttpResponse(html, content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.ticket_number}.html"'
    return response


@login_required
def download_all_tickets(request, order_id):
    """
    Download all tickets for an order as a single HTML file
    """
    order = get_object_or_404(
        Order.objects.prefetch_related('tickets__event', 'tickets__ticket_type'),
        id=order_id,
        user=request.user
    )
    
    tickets = order.tickets.all()
    
    if not tickets.exists():
        messages.error(request, "No tickets found.")
        return redirect('booking_confirmation', order_id=order.id)
    
    # Create combined HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>All Tickets - Order {order.order_number}</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
            .ticket-container {{ max-width: 800px; margin: 0 auto; }}
            .ticket-page {{ 
                background: white; 
                border-radius: 15px; 
                margin-bottom: 30px; 
                page-break-after: always;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            .ticket-header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                text-align: center;
            }}
            .ticket-body {{ padding: 20px; }}
            .info-row {{ margin-bottom: 10px; }}
            .info-label {{ font-weight: bold; color: #666; display: inline-block; width: 100px; }}
            .info-value {{ display: inline-block; color: #333; }}
            .qr-section {{ text-align: center; margin: 20px 0; }}
            .qr-section img {{ max-width: 150px; }}
            @media print {{
                .ticket-page {{ page-break-after: always; }}
            }}
        </style>
    </head>
    <body>
        <div class="ticket-container">
            <h2 style="text-align: center;">Order #{order.order_number}</h2>
            <p style="text-align: center;">Total Tickets: {tickets.count()}</p>
    """
    
    for ticket in tickets:
        # Convert QR code to base64
        qr_code_base64 = None
        if ticket.qr_code:
            try:
                with open(ticket.qr_code.path, 'rb') as f:
                    qr_code_base64 = base64.b64encode(f.read()).decode()
            except:
                pass
        
        html += f"""
        <div class="ticket-page">
            <div class="ticket-header">
                <h3>{ticket.event.title}</h3>
                <p>Ticket #{ticket.ticket_number}</p>
            </div>
            <div class="ticket-body">
                <div class="info-row">
                    <span class="info-label">Date:</span>
                    <span class="info-value">{ticket.event.start_date|date:"F d, Y"}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Time:</span>
                    <span class="info-value">{ticket.event.start_date|date:"g:i A"}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Venue:</span>
                    <span class="info-value">{ticket.event.venue_name}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Attendee:</span>
                    <span class="info-value">{ticket.attendee_name}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Ticket Type:</span>
                    <span class="info-value">{ticket.ticket_type.name}</span>
                </div>
        """
        
        if qr_code_base64:
            html += f"""
                <div class="qr-section">
                    <img src="data:image/png;base64,{qr_code_base64}" alt="QR Code">
                </div>
            """
        
        html += """
            </div>
        </div>
        """
    
    html += "</div></body></html>"
    
    response = HttpResponse(html, content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename="all_tickets_order_{order.order_number}.html"'
    return response