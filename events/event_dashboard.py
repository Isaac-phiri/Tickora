# views/event_management.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.http import JsonResponse

from dashboards.dashboard_base import AdminRequiredMixin, OrganizerRequiredMixin
from events.models import Event, EventCategory
from tickets.models import TicketType, Ticket
from orders.models import Order, OrderItem


class EventListView(OrganizerRequiredMixin, ListView):
    """List all events (filtered by user role)"""
    model = Event
    template_name = 'dashboard/events/event_list.html'
    context_object_name = 'events'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Event.objects.select_related(
            'organizer', 'category'
        ).prefetch_related('ticket_types')
        
        user = self.request.user
        
        if user.user_type == 'Admin':
            # Admin sees all events
            pass
        elif user.user_type == 'Staff':
            # Staff sees events they organize or co-organize
            queryset = queryset.filter(
                Q(organizer=user) | Q(co_organizers=user)
            )
        else:
            # Customers see published events only
            queryset = queryset.filter(status=Event.EventStatus.PUBLISHED)
        
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(venue_name__icontains=search) |
                Q(city__icontains=search)
            )
        
        return queryset.order_by('-start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = EventCategory.objects.all()
        context['status_choices'] = Event.EventStatus.choices
        context['current_status'] = self.request.GET.get('status', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context


class EventDetailView(OrganizerRequiredMixin, DetailView):
    """Detailed view of a single event with analytics"""
    model = Event
    template_name = 'dashboard/events/event_detail.html'
    context_object_name = 'event'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.get_object()
        
        # Ticket types with sales data
        ticket_types = event.ticket_types.annotate(
            tickets_sold_count=Count(
                'tickets',
                filter=Q(tickets__status__in=[Ticket.TicketStatus.VALID, Ticket.TicketStatus.USED])
            )
        )
        
        # Sales analytics
        total_tickets_sold = sum(tt.tickets_sold_count for tt in ticket_types)
        total_revenue = OrderItem.objects.filter(
            ticket_type__event=event,
            order__status=Order.OrderStatus.PAID
        ).aggregate(total=Sum('subtotal'))['total'] or 0
        
        # Order statistics
        total_orders = event.orders.filter(status=Order.OrderStatus.PAID).count()
        pending_orders = event.orders.filter(status=Order.OrderStatus.PENDING).count()
        
        # Daily sales data for chart
        sales_chart = self.get_sales_chart_data(event)
        
        # Recent orders for this event
        recent_orders = event.orders.select_related(
            'user'
        ).prefetch_related('order_items').order_by('-order_date')[:10]
        
        context.update({
            'ticket_types': ticket_types,
            'total_tickets_sold': total_tickets_sold,
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'sales_chart': sales_chart,
            'recent_orders': recent_orders,
            'is_organizer': event.organizer == self.request.user,
            'is_co_organizer': self.request.user in event.co_organizers.all(),
        })
        
        return context
    
    def get_sales_chart_data(self, event):
        """Generate daily sales data for the event"""
        chart_data = []
        now = timezone.now()
        
        # Get last 14 days or event lifetime
        days_to_show = min(14, (now - event.created_at).days) if event.created_at < now else 14
        
        for i in range(days_to_show - 1, -1, -1):
            date = now - timezone.timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            sales = OrderItem.objects.filter(
                ticket_type__event=event,
                order__status=Order.OrderStatus.PAID,
                order__order_date__range=(start_of_day, end_of_day)
            ).aggregate(total=Sum('subtotal'))['total'] or 0
            
            tickets_sold = OrderItem.objects.filter(
                ticket_type__event=event,
                order__status=Order.OrderStatus.PAID,
                order__order_date__range=(start_of_day, end_of_day)
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            chart_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'revenue': float(sales),
                'tickets': tickets_sold,
            })
        
        return chart_data


class EventCreateView(AdminRequiredMixin, CreateView):
    """Create a new event"""
    model = Event
    template_name = 'dashboard/events/event_form.html'
    fields = [
        'title', 'category', 'description', 'short_description',
        'start_date', 'end_date', 'door_open_time',
        'venue_name', 'venue_type', 'address_line1', 'address_line2',
        'city', 'state', 'country', 'postal_code', 'latitude', 'longitude',
        'virtual_meeting_url', 'virtual_meeting_password',
        'banner_image', 'thumbnail_image',
        'status', 'is_featured', 'is_private', 'invitation_code',
        'max_capacity', 'min_age_requirement',
        'tags', 'terms_and_conditions', 'refund_policy'
    ]
    
    def form_valid(self, form):
        form.instance.organizer = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Event "{self.object.title}" created successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Event'
        context['categories'] = EventCategory.objects.all()
        return context


class EventUpdateView(OrganizerRequiredMixin, UpdateView):
    """Update an existing event"""
    model = Event
    template_name = 'dashboard/events/event_form.html'
    fields = [
        'title', 'category', 'description', 'short_description',
        'start_date', 'end_date', 'door_open_time',
        'venue_name', 'venue_type', 'address_line1', 'address_line2',
        'city', 'state', 'country', 'postal_code', 'latitude', 'longitude',
        'virtual_meeting_url', 'virtual_meeting_password',
        'banner_image', 'thumbnail_image',
        'status', 'is_featured', 'is_private', 'invitation_code',
        'max_capacity', 'min_age_requirement',
        'tags', 'terms_and_conditions', 'refund_policy'
    ]
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Event "{self.object.title}" updated successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Event: {self.object.title}'
        context['categories'] = EventCategory.objects.all()
        return context


class EventDeleteView(AdminRequiredMixin, DeleteView):
    """Delete an event"""
    model = Event
    template_name = 'dashboard/events/event_confirm_delete.html'
    success_url = reverse_lazy('dashboard:event_list')
    
    def delete(self, request, *args, **kwargs):
        event = self.get_object()
        messages.success(request, f'Event "{event.title}" has been deleted.')
        return super().delete(request, *args, **kwargs)


class EventAnalyticsView(OrganizerRequiredMixin, DetailView):
    """Advanced analytics for an event"""
    model = Event
    template_name = 'dashboard/events/event_analytics.html'
    context_object_name = 'event'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.get_object()
        
        # Ticket sales by type
        ticket_sales = []
        for ticket_type in event.ticket_types.all():
            ticket_sales.append({
                'name': ticket_type.name,
                'sold': ticket_type.tickets_sold,
                'available': ticket_type.quantity_available,
                'revenue': ticket_type.tickets_sold * float(ticket_type.current_price),
            })
        
        # Sales over time (daily)
        sales_over_time = []
        current_date = event.created_at.date()
        end_date = timezone.now().date()
        
        while current_date <= end_date:
            start = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.min.time()))
            end = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.max.time()))
            
            daily_sales = OrderItem.objects.filter(
                ticket_type__event=event,
                order__status=Order.OrderStatus.PAID,
                order__order_date__range=(start, end)
            ).aggregate(
                revenue=Sum('subtotal'),
                tickets=Sum('quantity')
            )
            
            sales_over_time.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'revenue': float(daily_sales['revenue'] or 0),
                'tickets': daily_sales['tickets'] or 0,
            })
            
            current_date += timezone.timedelta(days=1)
        
        # Customer demographics
        unique_customers = Order.objects.filter(
            event=event,
            status=Order.OrderStatus.PAID
        ).values('user__email').distinct().count()
        
        # Check-in statistics
        total_checked_in = Ticket.objects.filter(
            event=event,
            status=Ticket.TicketStatus.USED
        ).count()
        
        check_in_rate = (total_checked_in / total_tickets_sold * 100) if total_tickets_sold > 0 else 0
        
        context.update({
            'ticket_sales': ticket_sales,
            'sales_over_time': sales_over_time,
            'unique_customers': unique_customers,
            'total_checked_in': total_checked_in,
            'check_in_rate': round(check_in_rate, 2),
            'total_revenue': sum(ts['revenue'] for ts in ticket_sales),
        })
        
        return context