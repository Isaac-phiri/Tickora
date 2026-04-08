# views/payment_management.py
from django.views.generic import ListView, DetailView
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal

from dashboards.dashboard_base import StaffRequiredMixin
from payments.models import Payment
from orders.models import Order


class PaymentListView(StaffRequiredMixin, ListView):
    """List all payments"""
    model = Payment
    template_name = 'dashboard/payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Payment.objects.select_related('order', 'user', 'order__event')
        
        # Apply filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        gateway = self.request.GET.get('gateway')
        if gateway:
            queryset = queryset.filter(gateway=gateway)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(transaction_id__icontains=search) |
                Q(order__order_number__icontains=search) |
                Q(user__email__icontains=search) |
                Q(order__email__icontains=search)
            )
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(payment_date__date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(payment_date__date__lte=date_to)
        
        # Staff only see payments for their events
        if self.request.user.user_type != 'Admin':
            queryset = queryset.filter(
                Q(order__event__organizer=self.request.user) |
                Q(order__event__co_organizers=self.request.user)
            )
        
        return queryset.order_by('-payment_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        queryset = self.get_queryset()
        
        # Summary statistics
        completed = queryset.filter(status=Payment.PaymentStatus.COMPLETED)
        context['summary'] = {
            'total_count': queryset.count(),
            'total_amount': completed.aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
            'total_fees': completed.aggregate(total=Sum('gateway_fee'))['total'] or Decimal('0.00'),
            'net_amount': completed.aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00'),
            'completed_count': completed.count(),
            'pending_count': queryset.filter(status=Payment.PaymentStatus.PENDING).count(),
            'failed_count': queryset.filter(status=Payment.PaymentStatus.FAILED).count(),
            'refunded_count': queryset.filter(status=Payment.PaymentStatus.REFUNDED).count(),
        }
        
        context['status_choices'] = Payment.PaymentStatus.choices
        context['gateway_choices'] = Payment.PaymentGateway.choices
        context['current_status'] = self.request.GET.get('status', '')
        context['current_gateway'] = self.request.GET.get('gateway', '')
        context['search_query'] = self.request.GET.get('search', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        return context


class PaymentDetailView(StaffRequiredMixin, DetailView):
    """Detailed view of a payment"""
    model = Payment
    template_name = 'dashboard/payments/payment_detail.html'
    context_object_name = 'payment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment = self.get_object()
        
        context['can_refund'] = (
            payment.status == Payment.PaymentStatus.COMPLETED and
            payment.refunded_amount < payment.amount
        )
        
        context['refundable_amount'] = payment.amount - payment.refunded_amount
        
        return context