from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def admin_required(view_func):
    """
    Decorator to check if user is admin
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('accounts:login')
        
        if request.user.user_type != 'Admin' and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('accounts:dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def staff_required(view_func):
    """
    Decorator to check if user is staff or admin
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('accounts:login')
        
        if request.user.user_type not in ['Admin', 'Staff'] and not request.user.is_staff:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('accounts:dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def customer_required(view_func):
    """
    Decorator for customer-only views
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)  # Allow guests?
        
        if request.user.user_type == 'Customer':
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, 'This area is for customers only.')
            return redirect('accounts:dashboard')
    return _wrapped_view


def organizer_required(view_func):
    """
    Decorator to check if user can manage events (Staff or Admin)
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('accounts:login')
        
        if request.user.user_type not in ['Admin', 'Staff']:
            messages.error(request, 'You need organizer privileges to access this page.')
            return redirect('accounts:dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view