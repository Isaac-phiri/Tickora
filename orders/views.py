from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import Order, OrderItem
from .cart import Cart
from tickets.models import TicketType, Ticket
from events.models import Event
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import stripe
from django.db.models import Q
from .forms import *
from dets.decorators import check_order_ownership, prevent_double_purchase


@login_required
@prevent_double_purchase
def checkout(request, event_id):
    """
    Checkout view - displays order summary and collects customer info
    """
    event = get_object_or_404(Event, pk=event_id)
    cart = get_cart(request)
    
    if not cart or cart.item_count == 0:
        messages.warning(request, "Your cart is empty.")
        return redirect('events:event_detail', pk=event_id)
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create order
                    order = Order.objects.create(
                        user=request.user,
                        email=form.cleaned_data['email'],
                        phone_number=form.cleaned_data['phone_number'],
                        event=event,
                        status='pending',
                        order_number=generate_order_number(),
                        expiry_date=timezone.now() + timezone.timedelta(minutes=30)
                    )
                    
                    # Create order items from cart
                    for item in cart.items.all():
                        ticket_type = item.ticket_type
                        
                        # Check availability
                        if ticket_type.tickets_remaining < item.quantity:
                            raise ValueError(f"Not enough tickets available for {ticket_type.name}")
                        
                        OrderItem.objects.create(
                            order=order,
                            ticket_type=ticket_type,
                            quantity=item.quantity,
                            unit_price=ticket_type.current_price
                        )
                    
                    # Calculate totals
                    order.calculate_totals()
                    
                    # Clear cart
                    clear_cart(request)
                    
                    # Redirect to payment
                    return redirect('payments:process_payment', order_id=order.id)
                    
            except Exception as e:
                logger.error(f"Checkout error: {str(e)}")
                messages.error(request, "An error occurred during checkout. Please try again.")
    else:
        initial = {
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        }
        form = CheckoutForm(initial=initial)
    
    context = {
        'event': event,
        'cart': cart,
        'form': form,
        'total': cart.total,
    }
    
    return render(request, 'orders/checkout.html', context)

def cart_detail(request):
    """
    View to display cart contents
    """
    cart = Cart(request)
    
    # Validate cart items
    is_valid, errors = cart.validate_availability()
    
    # Group items by event
    items_by_event = {}
    for item in cart:
        event_id = item['event_id']
        if event_id not in items_by_event:
            items_by_event[event_id] = {
                'event': item['ticket_type'].event if item.get('ticket_type') else None,
                'items': []
            }
        items_by_event[event_id]['items'].append(item)
    
    context = {
        'cart': cart,
        'items_by_event': items_by_event,
        'is_valid': is_valid,
        'errors': errors,
    }
    return render(request, 'orders/cart.html', context)


@require_POST
def cart_add(request, ticket_type_id):
    """
    Add a ticket to cart
    """
    ticket_type = get_object_or_404(TicketType, id=ticket_type_id)
    quantity = int(request.POST.get('quantity', 1))
    
    # Validate
    if quantity < ticket_type.min_per_order:
        messages.error(request, f'Minimum {ticket_type.min_per_order} ticket required.')
        return redirect('events:event_detail', slug=ticket_type.event.slug)
    
    if quantity > ticket_type.max_per_order:
        messages.error(request, f'Maximum {ticket_type.max_per_order} tickets allowed.')
        return redirect('events:event_detail', slug=ticket_type.event.slug)
    
    if quantity > ticket_type.tickets_remaining:
        messages.error(request, f'Only {ticket_type.tickets_remaining} tickets available.')
        return redirect('events:event_detail', slug=ticket_type.event.slug)
    
    cart = Cart(request)
    cart.add(ticket_type, quantity)
    
    messages.success(request, f'{quantity} x {ticket_type.name} added to cart.')
    
    # AJAX response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_total': len(cart),
            'cart_total_price': str(cart.get_total_price()),
        })
    
    return redirect('orders:cart_detail')


@require_POST
def cart_update(request, ticket_type_id):
    """
    Update quantity of a cart item
    """
    ticket_type = get_object_or_404(TicketType, id=ticket_type_id)
    quantity = int(request.POST.get('quantity', 1))
    
    cart = Cart(request)
    
    if quantity <= 0:
        cart.remove(ticket_type)
        messages.success(request, f'{ticket_type.name} removed from cart.')
    else:
        # Validate
        if quantity > ticket_type.tickets_remaining:
            messages.error(request, f'Only {ticket_type.tickets_remaining} tickets available.')
        elif quantity > ticket_type.max_per_order:
            messages.error(request, f'Maximum {ticket_type.max_per_order} tickets allowed.')
        else:
            cart.add(ticket_type, quantity, update_quantity=True)
            messages.success(request, f'Cart updated for {ticket_type.name}.')
    
    return redirect('orders:cart_detail')


@require_POST
def cart_remove(request, ticket_type_id):
    """
    Remove item from cart
    """
    ticket_type = get_object_or_404(TicketType, id=ticket_type_id)
    cart = Cart(request)
    cart.remove(ticket_type)
    
    messages.success(request, f'{ticket_type.name} removed from cart.')
    return redirect('orders:cart_detail')


def checkout_view(request):
    """
    Checkout process
    """
    cart = Cart(request)
    
    # Validate cart
    if len(cart) == 0:
        messages.warning(request, 'Your cart is empty.')
        return redirect('events:event_list')
    
    # Check if cart is valid
    is_valid, errors = cart.validate_availability()
    if not is_valid:
        for error in errors:
            messages.error(request, error)
        return redirect('orders:cart_detail')
    
    # Check if cart has items from multiple events
    if len(cart.get_event_ids()) > 1:
        messages.warning(request, 'Please complete separate orders for different events.')
        return redirect('orders:cart_detail')
    
    event_id = next(iter(cart.get_event_ids()))
    event = get_object_or_404(Event, id=event_id)
    
    if request.method == 'POST':
        # Process checkout
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        payment_method = request.POST.get('payment_method')
        
        if not email or not phone_number:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('orders:checkout')
        
        # Create order
        with transaction.atomic():
            # Re-validate availability
            for item in cart:
                ticket_type = TicketType.objects.select_for_update().get(id=item['ticket_type'].id)
                
                if item['quantity'] > ticket_type.tickets_remaining:
                    raise Exception(f'Not enough tickets for {ticket_type.name}')
            
            # Create order
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                email=email,
                phone_number=phone_number,
                event=event,
                is_guest_checkout=not request.user.is_authenticated,
                subtotal=cart.get_total_price(),
                total_amount=cart.get_total_price(),  # Will be recalculated with fees
            )
            
            # Create order items
            for item in cart:
                ticket_type = item['ticket_type']
                order_item = OrderItem.objects.create(
                    order=order,
                    ticket_type=ticket_type,
                    quantity=item['quantity'],
                    unit_price=item['price'],
                    subtotal=item['total_price'],
                )
                
                # Create individual tickets
                for i in range(item['quantity']):
                    Ticket.objects.create(
                        order=order,
                        order_item=order_item,
                        ticket_type=ticket_type,
                        event=event,
                    )
            
            # Recalculate totals
            order.calculate_totals()
            
            # Clear cart
            cart.clear()
            
            # Redirect to payment
            return redirect('payments:process', order_id=order.id)
    
    # Calculate totals
    subtotal = cart.get_total_price()
    service_fee = subtotal * Decimal('0.05')  # 5% service fee
    tax = subtotal * Decimal('0.08')  # 8% tax
    total = subtotal + service_fee + tax
    
    context = {
        'cart': cart,
        'event': event,
        'subtotal': subtotal,
        'service_fee': service_fee,
        'tax': tax,
        'total': total,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def order_history(request):
    """
    View user's order history
    """
    orders = Order.objects.filter(user=request.user).select_related(
        'event'
    ).prefetch_related(
        'order_items__ticket_type'
    ).order_by('-order_date')
    
    context = {
        'orders': orders,
    }
    return render(request, 'orders/order_history.html', context)


def order_confirmation(request, order_id):
    """
    Order confirmation page after successful payment
    """
    order = get_object_or_404(
        Order.objects.select_related('event', 'user').prefetch_related(
            'order_items__ticket_type',
            'tickets'
        ),
        id=order_id
    )
    
    # Security: check if user can view this order
    if order.user and request.user.is_authenticated and order.user != request.user:
        messages.error(request, 'You do not have permission to view this order.')
        return redirect('events:event_list')
    
    if not order.user and request.GET.get('email') != order.email:
        # For guest checkout, verify email
        if not request.session.get(f'order_{order.id}_viewed'):
            messages.error(request, 'Please check your email for the order confirmation link.')
            return redirect('events:event_list')
    
    # Mark as viewed in session for guests
    request.session[f'order_{order.id}_viewed'] = True
    
    context = {
        'order': order,
    }
    return render(request, 'orders/order_confirmation.html', context)


def order_tickets(request, order_id):
    """
    View all tickets for an order
    """
    order = get_object_or_404(
        Order.objects.prefetch_related(
            'tickets__event',
            'tickets__ticket_type'
        ),
        id=order_id
    )
    
    # Security check
    if order.user and request.user.is_authenticated and order.user != request.user:
        messages.error(request, 'You do not have permission to view these tickets.')
        return redirect('events:event_list')
    
    if not order.user and request.GET.get('email') != order.email:
        messages.error(request, 'Invalid access.')
        return redirect('events:event_list')
    
    tickets = order.tickets.all()
    
    context = {
        'order': order,
        'tickets': tickets,
    }
    return render(request, 'orders/order_tickets.html', context)


# Dashboard views
@login_required
def dashboard_order_list(request):
    """
    Dashboard view for orders (filtered by user role)
    """
    if request.user.user_type == 'Admin':
        orders = Order.objects.all().select_related('user', 'event')
    elif request.user.user_type == 'Staff':
        # Staff can see orders for events they organize
        orders = Order.objects.filter(
            event__in=request.user.organized_events.all()
        ).select_related('user', 'event')
    else:
        # Customers see only their orders
        orders = Order.objects.filter(user=request.user).select_related('event')
    
    # Apply filters
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    event_id = request.GET.get('event')
    if event_id:
        orders = orders.filter(event_id=event_id)
    
    date_from = request.GET.get('date_from')
    if date_from:
        orders = orders.filter(order_date__date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        orders = orders.filter(order_date__date__lte=date_to)
    
    search = request.GET.get('search')
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(email__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 20)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    # Get events for filter dropdown
    if request.user.user_type == 'Admin':
        events = Event.objects.all()
    elif request.user.user_type == 'Staff':
        events = request.user.organized_events.all()
    else:
        events = Event.objects.filter(orders__user=request.user).distinct()
    
    context = {
        'orders': orders,
        'events': events,
        'status': status,
        'event_id': event_id,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
    }
    return render(request, 'orders/dashboard/order_list.html', context)


@login_required
def dashboard_order_detail(request, pk):
    """
    Dashboard view for order details
    """
    if request.user.user_type == 'Admin':
        order = get_object_or_404(
            Order.objects.select_related('user', 'event').prefetch_related(
                'order_items__ticket_type',
                'tickets__ticket_type',
                'payment'
            ),
            pk=pk
        )
    elif request.user.user_type == 'Staff':
        order = get_object_or_404(
            Order.objects.filter(event__in=request.user.organized_events.all()).select_related(
                'user', 'event'
            ).prefetch_related(
                'order_items__ticket_type',
                'tickets__ticket_type',
                'payment'
            ),
            pk=pk
        )
    else:
        order = get_object_or_404(
            Order.objects.filter(user=request.user).select_related(
                'user', 'event'
            ).prefetch_related(
                'order_items__ticket_type',
                'tickets__ticket_type'
            ),
            pk=pk
        )
    
    context = {
        'order': order,
    }
    return render(request, 'orders/dashboard/order_detail.html', context)


@require_POST
@login_required
def dashboard_order_update_status(request, pk):
    """
    Update order status (Admin/Staff only)
    """
    if request.user.user_type not in ['Admin', 'Staff']:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    order = get_object_or_404(Order, pk=pk)
    new_status = request.POST.get('status')
    
    if new_status in dict(Order.OrderStatus.choices):
        order.status = new_status
        order.save()
        
        # Send email notification
        if new_status == 'cancelled':
            # TODO: Send cancellation email
            pass
        elif new_status == 'refunded':
            # TODO: Process refund
            pass
        
        return JsonResponse({'success': True, 'status': order.get_status_display()})
    
    return JsonResponse({'error': 'Invalid status'}, status=400)