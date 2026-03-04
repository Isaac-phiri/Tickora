from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from orders.models import Order


def organizer_required(view_func):
    """Decorator to check if user is an event organizer"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page.")
            return redirect('login')
        
        # Check if user has any events they organize
        if not request.user.organized_events.exists():
            messages.error(request, "You need to be an organizer to access this page.")
            return redirect('events:event_list')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def check_order_ownership(view_func):
    """Decorator to check if user owns the order"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        order_id = kwargs.get('order_id')
        try:
            order = Order.objects.get(id=order_id)
            if order.user != request.user and not request.user.is_staff:
                messages.error(request, "You don't have permission to view this order.")
                return redirect('orders:order_history')
        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect('orders:order_history')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def prevent_double_purchase(view_func):
    """Prevent purchasing same event twice"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        event_id = kwargs.get('event_id')
        
        if request.user.is_authenticated:
            # Check if user already has tickets for this event
            from tickets.models import Ticket
            if Ticket.objects.filter(
                order__user=request.user,
                event_id=event_id,
                status__in=['valid', 'used']
            ).exists():
                messages.warning(request, "You already have tickets for this event.")
                return redirect('events:event_detail', event_id=event_id)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view