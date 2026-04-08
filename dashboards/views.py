# views/dashboard_main.py
from decimal import Decimal

from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render

from .dashboard_base import DashboardRequiredMixin
from events.models import Event
from orders.models import Order
from payments.models import Payment
from tickets.models import Ticket
from django.views.generic import TemplateView


class DashboardHomeView(DashboardRequiredMixin, TemplateView):
    """Main dashboard view with role-based statistics"""
    template_name = 'dashboard/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.user_type == 'Admin':
            context.update(self.get_admin_stats())
        elif user.user_type == 'Staff':
            context.update(self.get_staff_stats())
        else:  # Customer
            context.update(self.get_customer_stats())
        
        return context
    
    def get_admin_stats(self):
        """Statistics for admin dashboard"""
        now = timezone.now()
        today = now.date()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week = now - timedelta(days=now.weekday())
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Revenue stats
        total_revenue = Payment.objects.filter(
            status=Payment.PaymentStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        today_revenue = Payment.objects.filter(
            status=Payment.PaymentStatus.COMPLETED,
            payment_date__gte=start_of_day
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        week_revenue = Payment.objects.filter(
            status=Payment.PaymentStatus.COMPLETED,
            payment_date__gte=start_of_week
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        month_revenue = Payment.objects.filter(
            status=Payment.PaymentStatus.COMPLETED,
            payment_date__gte=start_of_month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Order stats
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(
            status=Order.OrderStatus.PENDING
        ).count()
        completed_orders = Order.objects.filter(
            status=Order.OrderStatus.PAID
        ).count()
        
        # Event stats
        total_events = Event.objects.count()
        published_events = Event.objects.filter(
            status=Event.EventStatus.PUBLISHED
        ).count()
        upcoming_events = Event.objects.filter(
            start_date__gt=now,
            status=Event.EventStatus.PUBLISHED
        ).count()
        active_events = Event.objects.filter(
            start_date__lte=now,
            end_date__gte=now,
            status=Event.EventStatus.PUBLISHED
        ).count()
        
        # Ticket stats
        total_tickets_sold = Ticket.objects.filter(
            status__in=[Ticket.TicketStatus.VALID, Ticket.TicketStatus.USED]
        ).count()
        tickets_checked_in = Ticket.objects.filter(
            status=Ticket.TicketStatus.USED
        ).count()
        
        # User stats
        total_users = User.objects.count()
        customers = User.objects.filter(user_type='Customer').count()
        staff_members = User.objects.filter(user_type='Staff').count()
        
        # Recent data
        recent_orders = Order.objects.select_related(
            'user', 'event'
        ).order_by('-order_date')[:10]
        
        recent_events = Event.objects.select_related(
            'organizer', 'category'
        ).order_by('-created_at')[:10]
        
        # Chart data (last 7 days)
        revenue_chart = self.get_revenue_chart_data(7)
        
        return {
            'stats': {
                'total_revenue': total_revenue,
                'today_revenue': today_revenue,
                'week_revenue': week_revenue,
                'month_revenue': month_revenue,
                'total_orders': total_orders,
                'pending_orders': pending_orders,
                'completed_orders': completed_orders,
                'total_events': total_events,
                'published_events': published_events,
                'upcoming_events': upcoming_events,
                'active_events': active_events,
                'total_tickets_sold': total_tickets_sold,
                'tickets_checked_in': tickets_checked_in,
                'total_users': total_users,
                'customers': customers,
                'staff_members': staff_members,
            },
            'recent_orders': recent_orders,
            'recent_events': recent_events,
            'revenue_chart': revenue_chart,
        }
    
    def get_staff_stats(self):
        """Statistics for staff dashboard"""
        now = timezone.now()
        
        # Events managed by staff (if they are organizer or co-organizer)
        managed_events = Event.objects.filter(
            Q(organizer=self.request.user) | 
            Q(co_organizers=self.request.user)
        )
        
        total_managed_events = managed_events.count()
        upcoming_managed = managed_events.filter(
            start_date__gt=now,
            status=Event.EventStatus.PUBLISHED
        ).count()
        
        # Tickets checked in by this staff
        tickets_checked_in = Ticket.objects.filter(
            checked_in_by=self.request.user
        ).count()
        
        # Recent check-ins
        recent_checkins = Ticket.objects.filter(
            checked_in_by=self.request.user
        ).select_related('event', 'ticket_type', 'order').order_by('-checked_in_at')[:20]
        
        # Today's events for this staff
        today_events = managed_events.filter(
            start_date__date=now.date()
        )
        
        # Pending check-ins for today
        pending_checkins = Ticket.objects.filter(
            event__in=today_events,
            status=Ticket.TicketStatus.VALID
        ).count()
        
        return {
            'stats': {
                'total_managed_events': total_managed_events,
                'upcoming_managed': upcoming_managed,
                'tickets_checked_in': tickets_checked_in,
                'pending_checkins': pending_checkins,
            },
            'recent_checkins': recent_checkins,
            'today_events': today_events,
        }
    
    def get_customer_stats(self):
        """Statistics for customer dashboard"""
        user = self.request.user
        
        # Orders
        total_orders = Order.objects.filter(user=user).count()
        completed_orders = Order.objects.filter(
            user=user, 
            status=Order.OrderStatus.PAID
        ).count()
        
        # Tickets
        my_tickets = Ticket.objects.filter(
            order__user=user,
            status__in=[Ticket.TicketStatus.VALID, Ticket.TicketStatus.USED]
        )
        
        upcoming_tickets = my_tickets.filter(
            event__start_date__gt=timezone.now(),
            status=Ticket.TicketStatus.VALID
        ).count()
        
        past_tickets = my_tickets.filter(
            event__end_date__lt=timezone.now()
        ).count()
        
        # Total spent
        total_spent = Payment.objects.filter(
            order__user=user,
            status=Payment.PaymentStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Recent orders
        recent_orders = Order.objects.filter(
            user=user
        ).select_related('event').order_by('-order_date')[:5]
        
        # Upcoming events
        upcoming_events_attending = my_tickets.filter(
            event__start_date__gt=timezone.now(),
            status=Ticket.TicketStatus.VALID
        ).select_related('event', 'ticket_type').order_by('event__start_date')[:5]
        
        return {
            'stats': {
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'upcoming_tickets': upcoming_tickets,
                'past_tickets': past_tickets,
                'total_spent': total_spent,
            },
            'recent_orders': recent_orders,
            'upcoming_events': upcoming_events_attending,
        }
    
    def get_revenue_chart_data(self, days=7):
        """Generate revenue data for charts"""
        chart_data = []
        now = timezone.now()
        
        for i in range(days - 1, -1, -1):
            date = now - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            revenue = Payment.objects.filter(
                status=Payment.PaymentStatus.COMPLETED,
                payment_date__range=(start_of_day, end_of_day)
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            chart_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'revenue': float(revenue),
            })
        
        return chart_data