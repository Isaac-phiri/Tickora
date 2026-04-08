# utils/dashboard_utils.py
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.events.models import Event
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.tickets.models import Ticket


class DashboardStatsCalculator:
    """Helper class for calculating dashboard statistics"""
    
    def __init__(self, user=None):
        self.user = user
        self.now = timezone.now()
    
    def get_revenue_stats(self, days=30):
        """Get revenue statistics for the last N days"""
        start_date = self.now - timedelta(days=days)
        
        payments = Payment.objects.filter(
            status=Payment.PaymentStatus.COMPLETED,
            payment_date__gte=start_date
        )
        
        if self.user and self.user.user_type != 'Admin':
            payments = payments.filter(order__event__organizer=self.user)
        
        return {
            'total_revenue': payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
            'total_fees': payments.aggregate(total=Sum('gateway_fee'))['total'] or Decimal('0.00'),
            'net_revenue': payments.aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00'),
            'transaction_count': payments.count(),
        }
    
    def get_ticket_sales_stats(self, days=30):
        """Get ticket sales statistics"""
        start_date = self.now - timedelta(days=days)
        
        tickets = Ticket.objects.filter(
            created_at__gte=start_date,
            status__in=[Ticket.TicketStatus.VALID, Ticket.TicketStatus.USED]
        )
        
        if self.user and self.user.user_type != 'Admin':
            tickets = tickets.filter(event__organizer=self.user)
        
        return {
            'total_sold': tickets.count(),
            'total_checked_in': tickets.filter(status=Ticket.TicketStatus.USED).count(),
            'check_in_rate': 0,  # Calculate separately
        }
    
    def get_event_stats(self):
        """Get event statistics"""
        events = Event.objects.all()
        
        if self.user and self.user.user_type != 'Admin':
            events = events.filter(
                Q(organizer=self.user) | Q(co_organizers=self.user)
            )
        
        return {
            'total_events': events.count(),
            'published': events.filter(status=Event.EventStatus.PUBLISHED).count(),
            'draft': events.filter(status=Event.EventStatus.DRAFT).count(),
            'upcoming': events.filter(
                start_date__gt=self.now,
                status=Event.EventStatus.PUBLISHED
            ).count(),
            'active': events.filter(
                start_date__lte=self.now,
                end_date__gte=self.now,
                status=Event.EventStatus.PUBLISHED
            ).count(),
            'completed': events.filter(
                end_date__lt=self.now,
                status=Event.EventStatus.COMPLETED
            ).count(),
        }
    
    def get_order_stats(self):
        """Get order statistics"""
        orders = Order.objects.all()
        
        if self.user and self.user.user_type != 'Admin':
            orders = orders.filter(event__organizer=self.user)
        
        return {
            'total_orders': orders.count(),
            'pending': orders.filter(status=Order.OrderStatus.PENDING).count(),
            'paid': orders.filter(status=Order.OrderStatus.PAID).count(),
            'cancelled': orders.filter(status=Order.OrderStatus.CANCELLED).count(),
            'expired': orders.filter(status=Order.OrderStatus.EXPIRED).count(),
            'average_order_value': orders.filter(
                status=Order.OrderStatus.PAID
            ).aggregate(avg=Sum('total_amount'))['avg'] or Decimal('0.00'),
        }