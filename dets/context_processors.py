from cart.utils import get_cart


def cart_processor(request):
    """Add cart to template context"""
    if request.user.is_authenticated:
        cart = get_cart(request)
        return {
            'cart_count': cart.item_count if cart else 0,
            'cart_total': cart.total if cart else 0
        }
    return {
        'cart_count': 0,
        'cart_total': 0
    }


def notifications_processor(request):
    """Add notifications to template context"""
    if request.user.is_authenticated:
        from notifications.models import Notification
        unread_count = Notification.objects.filter(
            user=request.user,
            read=False
        ).count()
        return {
            'unread_notifications': unread_count
        }
    return {'unread_notifications': 0}