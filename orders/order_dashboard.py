# views/order_management.py
from django.views.generic import ListView, DetailView, UpdateView
from django.contrib import messages
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse

from dashboards.dashboard_base import AdminRequiredMixin, StaffRequiredMixin
from orders.models import Order, OrderItem
from payments.models import Payment


class OrderListView(StaffRequiredMixin, ListView):
    """List all orders with filtering options"""
    model = Order
    template_name = 'dashboard/orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Order.objects.select_related(
            'user', 'event', 'payment'
        ).prefetch_related('order_items')
        
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        event_id = self.request.GET.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(order_date__date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(order_date__date__lte=date_to)
        
        # Filter by user type (if staff)
        if self.request.user.user_type != 'Admin':
            queryset = queryset.filter(event__organizer=self.request.user)
        
        return queryset.order_by('-order_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Summary statistics
        orders = self.get_queryset()
        context['summary'] = {
            'total_orders': orders.count(),
            'total_revenue': orders.filter(
                status=Order.OrderStatus.PAID
            ).aggregate(total=Sum('total_amount'))['total'] or 0,
            'pending_orders': orders.filter(status=Order.OrderStatus.PENDING).count(),
            'completed_orders': orders.filter(status=Order.OrderStatus.PAID).count(),
        }
        
        # Filters context
        from events.models import Event
        context['status_choices'] = Order.OrderStatus.choices
        context['events'] = Event.objects.all()
        context['current_status'] = self.request.GET.get('status', '')
        context['current_event'] = self.request.GET.get('event', '')
        context['search_query'] = self.request.GET.get('search', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        return context


class OrderDetailView(StaffRequiredMixin, DetailView):
    """Detailed view of a single order"""
    model = Order
    template_name = 'dashboard/orders/order_detail.html'
    context_object_name = 'order'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        
        # Order items with ticket details
        order_items = order.order_items.select_related('ticket_type').all()
        
        # Tickets for this order
        tickets = order.tickets.select_related('ticket_type', 'event').all()
        
        # Payment details
        payment = getattr(order, 'payment', None)
        
        # Calculate order totals if not already calculated
        if order.total_amount == 0:
            order.calculate_totals()
        
        context.update({
            'order_items': order_items,
            'tickets': tickets,
            'payment': payment,
            'can_cancel': order.status in [Order.OrderStatus.PENDING, Order.OrderStatus.PROCESSING],
            'can_refund': order.status == Order.OrderStatus.PAID and payment and payment.status == Payment.PaymentStatus.COMPLETED,
        })
        
        return context


class OrderStatusUpdateView(StaffRequiredMixin, UpdateView):
    """Update order status"""
    model = Order
    fields = ['status']
    template_name = 'dashboard/orders/order_status_update.html'
    
    def form_valid(self, form):
        old_status = self.get_object().status
        new_status = form.cleaned_data['status']
        
        response = super().form_valid(form)
        
        message = f'Order {self.object.order_number} status changed from {old_status} to {new_status}'
        messages.success(self.request, message)
        
        return response
    
    def get_success_url(self):
        return reverse('dashboard:order_detail', kwargs={'pk': self.object.pk})


class OrderExportView(StaffRequiredMixin, ListView):
    """Export orders as CSV"""
    model = Order
    template_name = 'dashboard/orders/order_export.html'
    
    def get(self, request, *args, **kwargs):
        import csv
        from django.http import HttpResponse
        
        queryset = self.get_queryset()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Order Number', 'Customer Email', 'Event', 'Status',
            'Subtotal', 'Total Amount', 'Order Date', 'Payment Status'
        ])
        
        for order in queryset:
            writer.writerow([
                order.order_number,
                order.email,
                order.event.title,
                order.status,
                order.subtotal,
                order.total_amount,
                order.order_date.strftime('%Y-%m-%d %H:%M'),
                getattr(order.payment, 'status', 'N/A') if hasattr(order, 'payment') else 'No Payment'
            ])
        
        return response
    
    def get_queryset(self):
        queryset = Order.objects.select_related('event')
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(order_date__date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(order_date__date__lte=date_to)
        
        return queryset