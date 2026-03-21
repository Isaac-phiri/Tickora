from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from decimal import Decimal
import uuid
import logging

from orders.models import Cart, CartItem
from events.models import Event
from tickets.models import TicketType

logger = logging.getLogger(__name__)


def get_cart(request):
    """
    Get or create a cart for the current user/session.
    Handles both authenticated users and guest sessions.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Cart object: The user's active cart
    """
    cart = None
    
    # For authenticated users, get cart by user
    if request.user.is_authenticated:
        cart = get_cart_for_user(request.user)
        
        # If user had a session cart, merge it
        if request.session.get('cart_id'):
            session_cart = get_cart_by_session(request.session.get('cart_id'))
            if session_cart and session_cart.user is None:
                merge_carts(session_cart, cart)
                request.session.pop('cart_id', None)
    
    # For anonymous users, get cart by session
    else:
        cart_id = request.session.get('cart_id')
        if cart_id:
            cart = get_cart_by_session(cart_id)
        
        # If no cart exists, create one
        if not cart:
            cart = create_session_cart(request)
    
    return cart


def get_cart_for_user(user):
    """
    Get active cart for authenticated user.
    Creates a new cart if none exists.
    
    Args:
        user: User object
        
    Returns:
        Cart: User's active cart
    """
    try:
        cart = Cart.objects.get(user=user, is_active=True)
    except Cart.DoesNotExist:
        cart = Cart.objects.create(
            user=user,
            session_id=None,
            cart_number=generate_cart_number(),
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )
        logger.info(f"Created new cart for user {user.id}")
    
    return cart


def get_cart_by_session(cart_id):
    """
    Get cart by session ID.
    
    Args:
        cart_id: Cart ID from session
        
    Returns:
        Cart object or None
    """
    try:
        cart = Cart.objects.get(id=cart_id, is_active=True)
        
        # Check if cart is expired
        if cart.expires_at < timezone.now():
            cart.is_active = False
            cart.save()
            return None
        
        return cart
    except (Cart.DoesNotExist, ValueError):
        return None


def create_session_cart(request):
    """
    Create a new session-based cart for anonymous user.
    
    Args:
        request: HTTP request object
        
    Returns:
        Cart: Newly created cart
    """
    cart = Cart.objects.create(
        user=None,
        session_id=request.session.session_key or generate_session_id(request),
        cart_number=generate_cart_number(),
        expires_at=timezone.now() + timezone.timedelta(days=7)
    )
    
    request.session['cart_id'] = cart.id
    logger.info(f"Created new session cart {cart.id}")
    
    return cart


def merge_carts(source_cart, target_cart):
    """
    Merge items from source cart into target cart.
    Used when anonymous user logs in.
    
    Args:
        source_cart: Cart to merge from (usually session cart)
        target_cart: Cart to merge into (usually user cart)
    """
    if not source_cart or not target_cart:
        return
    
    for item in source_cart.items.all():
        try:
            # Check if item already exists in target cart
            existing_item = target_cart.items.get(
                ticket_type=item.ticket_type
            )
            # Update quantity
            existing_item.quantity += item.quantity
            existing_item.save()
        except CartItem.DoesNotExist:
            # Transfer item to target cart
            item.cart = target_cart
            item.save()
    
    # Deactivate source cart
    source_cart.is_active = False
    source_cart.save()
    
    logger.info(f"Merged cart {source_cart.id} into {target_cart.id}")


def add_to_cart(request, ticket_type_id, quantity=1):
    """
    Add item to cart.
    
    Args:
        request: HTTP request object
        ticket_type_id: ID of ticket type to add
        quantity: Quantity to add
        
    Returns:
        tuple: (cart_item, created)
    """
    cart = get_cart(request)
    ticket_type = TicketType.objects.select_related('event').get(id=ticket_type_id)
    
    # Check availability
    if ticket_type.tickets_remaining < quantity:
        raise ValueError(f"Only {ticket_type.tickets_remaining} tickets available")
    
    # Check max per order
    if quantity > ticket_type.max_per_order:
        raise ValueError(f"Maximum {ticket_type.max_per_order} tickets per order")
    
    # Check if item already exists in cart
    try:
        cart_item = CartItem.objects.get(
            cart=cart,
            ticket_type=ticket_type
        )
        # Update quantity
        new_quantity = cart_item.quantity + quantity
        
        # Check max per order
        if new_quantity > ticket_type.max_per_order:
            raise ValueError(f"Cannot add more than {ticket_type.max_per_order} tickets")
        
        # Check availability
        if new_quantity > ticket_type.tickets_remaining:
            raise ValueError(f"Only {ticket_type.tickets_remaining} tickets available")
        
        cart_item.quantity = new_quantity
        cart_item.save()
        created = False
        
    except CartItem.DoesNotExist:
        # Create new cart item
        cart_item = CartItem.objects.create(
            cart=cart,
            ticket_type=ticket_type,
            quantity=quantity,
            unit_price=ticket_type.current_price
        )
        created = True
    
    # Update cart totals
    cart.update_totals()
    
    logger.info(f"Added {quantity}x {ticket_type.name} to cart {cart.id}")
    
    return cart_item, created


def remove_from_cart(request, item_id):
    """
    Remove item from cart.
    
    Args:
        request: HTTP request object
        item_id: CartItem ID to remove
        
    Returns:
        bool: True if removed, False if not found
    """
    cart = get_cart(request)
    
    try:
        cart_item = CartItem.objects.get(id=item_id, cart=cart)
        cart_item.delete()
        
        # Update cart totals
        cart.update_totals()
        
        logger.info(f"Removed item {item_id} from cart {cart.id}")
        return True
        
    except CartItem.DoesNotExist:
        return False


def update_cart_quantity(request, item_id, quantity):
    """
    Update quantity of cart item.
    
    Args:
        request: HTTP request object
        item_id: CartItem ID
        quantity: New quantity
        
    Returns:
        CartItem: Updated cart item
    """
    cart = get_cart(request)
    cart_item = CartItem.objects.get(id=item_id, cart=cart)
    ticket_type = cart_item.ticket_type
    
    if quantity <= 0:
        cart_item.delete()
        cart.update_totals()
        return None
    
    # Check max per order
    if quantity > ticket_type.max_per_order:
        raise ValueError(f"Maximum {ticket_type.max_per_order} tickets per order")
    
    # Check availability
    if quantity > ticket_type.tickets_remaining:
        raise ValueError(f"Only {ticket_type.tickets_remaining} tickets available")
    
    cart_item.quantity = quantity
    cart_item.save()
    
    # Update cart totals
    cart.update_totals()
    
    logger.info(f"Updated item {item_id} quantity to {quantity} in cart {cart.id}")
    
    return cart_item


def clear_cart(request):
    """
    Remove all items from cart.
    
    Args:
        request: HTTP request object
    """
    cart = get_cart(request)
    cart.items.all().delete()
    cart.update_totals()
    logger.info(f"Cleared cart {cart.id}")


def get_cart_summary(request):
    """
    Get cart summary data for display.
    
    Args:
        request: HTTP request object
        
    Returns:
        dict: Cart summary information
    """
    cart = get_cart(request)
    items = cart.items.select_related('ticket_type__event').all()
    
    summary = {
        'cart': cart,
        'items': items,
        'item_count': cart.item_count,
        'subtotal': cart.subtotal,
        'service_fee': cart.service_fee,
        'total': cart.total,
        'events': {},
    }
    
    # Group items by event
    for item in items:
        event = item.ticket_type.event
        if event.id not in summary['events']:
            summary['events'][event.id] = {
                'event': event,
                'items': [],
                'subtotal': Decimal('0.00'),
            }
        
        summary['events'][event.id]['items'].append(item)
        summary['events'][event.id]['subtotal'] += item.subtotal
    
    return summary


def check_cart_availability(cart):
    """
    Check if all items in cart are still available.
    
    Args:
        cart: Cart object
        
    Returns:
        tuple: (is_available, unavailable_items)
    """
    unavailable_items = []
    
    for item in cart.items.select_related('ticket_type').all():
        ticket_type = item.ticket_type
        
        # Check if ticket type still exists and is active
        if not ticket_type or not ticket_type.is_active:
            unavailable_items.append({
                'item': item,
                'reason': 'Ticket type no longer available'
            })
            continue
        
        # Check if still within sales period
        now = timezone.now()
        if now < ticket_type.sales_start_date or now > ticket_type.sales_end_date:
            unavailable_items.append({
                'item': item,
                'reason': 'Sales period has ended'
            })
            continue
        
        # Check quantity available
        if item.quantity > ticket_type.tickets_remaining:
            unavailable_items.append({
                'item': item,
                'reason': f'Only {ticket_type.tickets_remaining} tickets available'
            })
    
    return len(unavailable_items) == 0, unavailable_items


def cleanup_expired_carts():
    """
    Clean up expired carts.
    Should be called periodically via cron or Celery.
    
    Returns:
        int: Number of carts cleaned up
    """
    expired_carts = Cart.objects.filter(
        expires_at__lt=timezone.now(),
        is_active=True
    )
    
    count = expired_carts.count()
    expired_carts.update(is_active=False)
    
    logger.info(f"Cleaned up {count} expired carts")
    
    return count


def generate_cart_number():
    """
    Generate unique cart number.
    
    Returns:
        str: Unique cart number
    """
    return f"CART-{uuid.uuid4().hex[:10].upper()}"


def generate_session_id(request):
    """
    Generate session ID if not exists.
    
    Args:
        request: HTTP request object
        
    Returns:
        str: Session ID
    """
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_cart_item_count(request):
    """
    Get total number of items in cart.
    
    Args:
        request: HTTP request object
        
    Returns:
        int: Total items count
    """
    cart = get_cart(request)
    return cart.item_count


def get_cart_total(request):
    """
    Get cart total.
    
    Args:
        request: HTTP request object
        
    Returns:
        Decimal: Cart total
    """
    cart = get_cart(request)
    return cart.total


def validate_cart_for_checkout(request):
    """
    Validate cart before proceeding to checkout.
    
    Args:
        request: HTTP request object
        
    Returns:
        tuple: (is_valid, errors, warnings)
    """
    cart = get_cart(request)
    errors = []
    warnings = []
    
    if cart.item_count == 0:
        errors.append("Your cart is empty")
        return False, errors, warnings
    
    # Check availability
    is_available, unavailable_items = check_cart_availability(cart)
    if not is_available:
        for item in unavailable_items:
            errors.append(item['reason'])
        return False, errors, warnings
    
    # Check for price changes
    for item in cart.items.select_related('ticket_type').all():
        current_price = item.ticket_type.current_price
        if current_price != item.unit_price:
            warnings.append({
                'item': item,
                'old_price': item.unit_price,
                'new_price': current_price
            })
    
    # Check event status
    for item in cart.items.select_related('ticket_type__event').all():
        event = item.ticket_type.event
        if event.status != 'published':
            errors.append(f"{event.title} is no longer available")
        elif event.is_sold_out:
            errors.append(f"{event.title} is sold out")
    
    return len(errors) == 0, errors, warnings


def transfer_cart_to_user(request, user):
    """
    Transfer session cart to authenticated user.
    
    Args:
        request: HTTP request object
        user: User object
        
    Returns:
        Cart: User's cart
    """
    session_cart = None
    cart_id = request.session.get('cart_id')
    
    if cart_id:
        session_cart = get_cart_by_session(cart_id)
    
    # Get or create user cart
    user_cart, created = Cart.objects.get_or_create(
        user=user,
        is_active=True,
        defaults={
            'cart_number': generate_cart_number(),
            'expires_at': timezone.now() + timezone.timedelta(days=7)
        }
    )
    
    # Merge if session cart exists
    if session_cart and session_cart.user is None:
        merge_carts(session_cart, user_cart)
        request.session.pop('cart_id', None)
    
    return user_cart