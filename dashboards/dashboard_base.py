# views/dashboard_base.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q
from django.utils import timezone
from decimal import Decimal

from accounts.models import User
from events.models import Event
from orders.models import Order, OrderItem
from payments.models import Payment
from tickets.models import Ticket, TicketType


class DashboardRequiredMixin(LoginRequiredMixin):
    """Base mixin for all dashboard views"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_type'] = self.request.user.user_type
        return context


class AdminRequiredMixin(DashboardRequiredMixin):
    """Mixin for admin-only views"""
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'Admin' and not request.user.is_superuser:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class StaffRequiredMixin(DashboardRequiredMixin):
    """Mixin for staff and admin views"""
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type not in ['Admin', 'Staff'] and not request.user.is_staff:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class OrganizerRequiredMixin(DashboardRequiredMixin):
    """Mixin for event organizers"""
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.user_type not in ['Admin', 'Staff'] and not user.is_staff:
            event_id = self.kwargs.get('event_id')
            if event_id:
                event = Event.objects.get(id=event_id)
                if event.organizer != user and user not in event.co_organizers.all():
                    return self.handle_no_permission()
            else:
                if not Event.objects.filter(
                    Q(organizer=user) | Q(co_organizers=user)
                ).exists():
                    return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)