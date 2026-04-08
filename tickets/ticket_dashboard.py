# views/ticket_management.py
from django.db import models
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

from dashboards.dashboard_base import StaffRequiredMixin, OrganizerRequiredMixin
from tickets.models import Ticket, TicketType
from events.models import Event


class TicketTypeListView(OrganizerRequiredMixin, ListView):
    """List all ticket types for an event"""
    model = TicketType
    template_name = 'dashboard/tickets/ticket_type_list.html'
    context_object_name = 'ticket_types'
    
    def get_queryset(self):
        event_id = self.kwargs.get('event_id')
        self.event = get_object_or_404(Event, id=event_id)
        return self.event.ticket_types.all().annotate(
            tickets_sold_count=models.Count(
                'tickets',
                filter=models.Q(tickets__status__in=[Ticket.TicketStatus.VALID, Ticket.TicketStatus.USED])
            )
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        return context


class TicketTypeCreateView(OrganizerRequiredMixin, CreateView):
    """Create a new ticket type for an event"""
    model = TicketType
    template_name = 'dashboard/tickets/ticket_type_form.html'
    fields = [
        'name', 'ticket_class', 'description', 'price',
        'early_bird_price', 'early_bird_end_date',
        'quantity_available', 'max_per_order', 'min_per_order',
        'sales_start_date', 'sales_end_date',
        'service_fee_percentage', 'service_fee_fixed'
    ]
    
    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(Event, id=kwargs.get('event_id'))
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.event = self.event
        response = super().form_valid(form)
        messages.success(self.request, f'Ticket type "{self.object.name}" created successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        context['title'] = f'Add Ticket Type - {self.event.title}'
        return context
    
    def get_success_url(self):
        return reverse('dashboard:ticket_type_list', kwargs={'event_id': self.event.id})


class TicketTypeUpdateView(OrganizerRequiredMixin, UpdateView):
    """Update an existing ticket type"""
    model = TicketType
    template_name = 'dashboard/tickets/ticket_type_form.html'
    fields = [
        'name', 'ticket_class', 'description', 'price',
        'early_bird_price', 'early_bird_end_date',
        'quantity_available', 'max_per_order', 'min_per_order',
        'sales_start_date', 'sales_end_date',
        'service_fee_percentage', 'service_fee_fixed'
    ]
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Ticket type "{self.object.name}" updated successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.object.event
        context['title'] = f'Edit Ticket Type - {self.object.name}'
        return context
    
    def get_success_url(self):
        return reverse('dashboard:ticket_type_list', kwargs={'event_id': self.object.event.id})


class TicketListView(StaffRequiredMixin, ListView):
    """List all tickets with filtering"""
    model = Ticket
    template_name = 'dashboard/tickets/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Ticket.objects.select_related(
            'event', 'ticket_type', 'order', 'order__user'
        )
        
        # Filter by event
        event_id = self.kwargs.get('event_id')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
            self.event = get_object_or_404(Event, id=event_id)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by check-in status
        checked_in = self.request.GET.get('checked_in')
        if checked_in == 'yes':
            queryset = queryset.filter(status=Ticket.TicketStatus.USED)
        elif checked_in == 'no':
            queryset = queryset.filter(status=Ticket.TicketStatus.VALID)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(ticket_number__icontains=search) |
                Q(attendee_name__icontains=search) |
                Q(attendee_email__icontains=search) |
                Q(order__email__icontains=search)
            )
        
        # Filter by date
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Staff only see their events
        if self.request.user.user_type != 'Admin':
            queryset = queryset.filter(
                Q(event__organizer=self.request.user) |
                Q(event__co_organizers=self.request.user)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if hasattr(self, 'event'):
            context['event'] = self.event
            context['event_id'] = self.event.id
        
        # Summary statistics
        queryset = self.get_queryset()
        context['summary'] = {
            'total': queryset.count(),
            'valid': queryset.filter(status=Ticket.TicketStatus.VALID).count(),
            'used': queryset.filter(status=Ticket.TicketStatus.USED).count(),
            'refunded': queryset.filter(status=Ticket.TicketStatus.REFUNDED).count(),
        }
        
        context['status_choices'] = Ticket.TicketStatus.choices
        context['current_status'] = self.request.GET.get('status', '')
        context['checked_in_filter'] = self.request.GET.get('checked_in', '')
        context['search_query'] = self.request.GET.get('search', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        return context


class TicketDetailView(StaffRequiredMixin, DetailView):
    """Detailed view of a single ticket"""
    model = Ticket
    template_name = 'dashboard/tickets/ticket_detail.html'
    context_object_name = 'ticket'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ticket = self.get_object()
        
        context['can_check_in'] = (
            ticket.status == Ticket.TicketStatus.VALID and
            ticket.event.start_date <= timezone.now() <= ticket.event.end_date
        )
        
        return context


class TicketCheckInView(StaffRequiredMixin, UpdateView):
    """Check in a ticket"""
    model = Ticket
    fields = []
    http_method_names = ['post']
    
    def post(self, request, *args, **kwargs):
        ticket = self.get_object()
        
        if ticket.status != Ticket.TicketStatus.VALID:
            return JsonResponse({
                'success': False,
                'error': f'Cannot check in ticket with status: {ticket.status}'
            }, status=400)
        
        if ticket.event.start_date > timezone.now():
            return JsonResponse({
                'success': False,
                'error': 'Event has not started yet'
            }, status=400)
        
        try:
            ticket.check_in(
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Ticket {ticket.ticket_number} checked in successfully',
                'checked_in_at': ticket.checked_in_at.isoformat()
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class BulkTicketCheckInView(StaffRequiredMixin, ListView):
    """Bulk check-in tickets via QR code scanner"""
    template_name = 'dashboard/tickets/bulk_checkin.html'
    
    def get_queryset(self):
        event_id = self.kwargs.get('event_id')
        self.event = get_object_or_404(Event, id=event_id)
        
        return Ticket.objects.filter(
            event=self.event,
            status=Ticket.TicketStatus.VALID
        ).select_related('ticket_type', 'order')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.event
        
        # Statistics
        total_tickets = Ticket.objects.filter(event=self.event).count()
        checked_in = Ticket.objects.filter(
            event=self.event,
            status=Ticket.TicketStatus.USED
        ).count()
        
        context['stats'] = {
            'total': total_tickets,
            'checked_in': checked_in,
            'remaining': total_tickets - checked_in,
            'percentage': (checked_in / total_tickets * 100) if total_tickets > 0 else 0,
        }
        
        return context
    
    def post(self, request, *args, **kwargs):
        event_id = self.kwargs.get('event_id')
        ticket_data = request.POST.get('ticket_data', '')
        
        # Parse QR code data
        if ticket_data.startswith('TICKET:'):
            parts = ticket_data.split(':')
            if len(parts) >= 3:
                ticket_number = parts[1]
                qr_secret = parts[2]
                
                try:
                    ticket = Ticket.objects.get(
                        ticket_number=ticket_number,
                        qr_secret=qr_secret,
                        event_id=event_id,
                        status=Ticket.TicketStatus.VALID
                    )
                    
                    ticket.check_in(
                        user=request.user,
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'Checked in: {ticket.ticket_number}',
                        'attendee': ticket.attendee_name or ticket.order.email,
                        'ticket_type': ticket.ticket_type.name
                    })
                except Ticket.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid or already used ticket'
                    }, status=400)
        
        return JsonResponse({
            'success': False,
            'error': 'Invalid QR code'
        }, status=400)


class TicketExportView(StaffRequiredMixin, ListView):
    """Export tickets as CSV"""
    
    def get(self, request, *args, **kwargs):
        import csv
        from django.http import HttpResponse
        
        event_id = self.kwargs.get('event_id')
        queryset = Ticket.objects.filter(event_id=event_id).select_related(
            'ticket_type', 'order', 'order__user'
        )
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tickets_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Ticket Number', 'Event', 'Ticket Type', 'Status',
            'Attendee Name', 'Attendee Email', 'Order Number',
            'Customer Email', 'Checked In At', 'Checked In By'
        ])
        
        for ticket in queryset:
            writer.writerow([
                ticket.ticket_number,
                ticket.event.title,
                ticket.ticket_type.name,
                ticket.status,
                ticket.attendee_name,
                ticket.attendee_email,
                ticket.order.order_number,
                ticket.order.email,
                ticket.checked_in_at.strftime('%Y-%m-%d %H:%M') if ticket.checked_in_at else '',
                ticket.checked_in_by.full_name if ticket.checked_in_by else '',
            ])
        
        return response