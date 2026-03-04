from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.db.models import Q
from .models import *
from .forms import *
from events.managers import TicketManager
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from tickets.models import Ticket
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone



class EventListView(ListView):
    model = Event
    template_name = 'event/event_list.html'
    context_object_name = 'events'
    paginate_by = 6

# class EventHomePageListView(ListView):
#     model = Event
#     template_name = 'home/homepage.html'
#     login_url = 'login'
#     paginate_by = 4

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context["events_list"] = Event.objects.all().order_by('-timestamp') 
#         context['events'] = Event.objects.all()
#         context['latest'] = Event.get_latest_events()
#         return context


class EventHomePageListView(TemplateView):
    template_name = 'home/homepage.html'
    paginate_by = 6  # Items per page

    def get_latest_events(self):
        return self.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the type parameter from URL
        listing_type = self.request.GET.get('type')
        
        # Event listing
        event_list = Event.objects.all().order_by('-created_at')
        event_paginator = Paginator(event_list, self.paginate_by)
        event_page = self.request.GET.get('event_page', 1)
        context['events_list'] = event_paginator.get_page(event_page)
        context['events'] = Event.objects.all()
        context['latest'] = Event.get_latest_events()
        
        # Pass the active tab type
        context['active_tab'] = listing_type
        
        return context

class AboutUsView(TemplateView):
    template_name = 'home/about_us.html'
    login_url = 'login'

class ContactView(TemplateView):
    template_name = 'home/contact.html'
    login_url = 'login'

class ServicesView(TemplateView):
    template_name = 'home/services.html'
    login_url = 'login'

# class LatestEventListView(ListView):
#     model = Event
#     template_name = 'home/homepage.html'
#     context_object_name = 'latest_events'

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['latest_events'] = Event.objects.latest_events(limit=5)
#         return context


# @method_decorator(login_required, name='dispatch')
class EventDetailView(DetailView):
    model = Event
    template_name = 'event/event_detail.html'
    context_object_name = 'event'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.get_object()
        
        # Get all ticket types for this event (not from Ticket objects)
        ticket_types = TicketType.objects.filter(
            event=event,
            is_active=True  # Only active ticket types
        ).order_by('price')  # Order by price
        
        # You might also want to filter by sales dates
        # current_time = timezone.now()
        # ticket_types = ticket_types.filter(
        #     sales_start_date__lte=current_time,
        #     sales_end_date__gte=current_time
        # )
        
        context['ticket_types'] = ticket_types
        context['now'] = timezone.now()  # For early bird comparison in template
        
        # Debug: print to console to verify
        print(f"Event: {event.title}")
        print(f"Found {ticket_types.count()} ticket types")
        for tt in ticket_types:
            print(f"  - {tt.name}: K{tt.price}, Available: {tt.quantity_available}")
        
        return context
    
# @method_decorator(login_required, name='dispatch')
class EventCreateView(CreateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('event-list')
    

class EventUpdateView(UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('event-list')

class EventDeleteView(DeleteView):
    model = Event
    template_name = 'events/event_confirm_delete.html'
    success_url = reverse_lazy('event-list')

class EventStatusListView(ListView):
    model = Event
    template_name = 'events/event_status_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        status = self.kwargs.get('status')
        return Event.objects.filter(status=status)


class EventSearchListView(ListView):
    template_name = 'event/event_list.html'
    context_object_name = 'events'

    def get_queryset(self):
        query = self.request.GET.get('q')
        event_type = self.request.GET.get('event_type', None)
        
        # Start with all active events
        events = Event.objects.filter(status='Active')
        
        # Filter by search query
        if query:
            events = events.filter(
                Q(event_name__icontains=query) | 
                Q(description__icontains=query)
            )
        
        # Filter by event type
        if event_type:
            events = events.filter(event_type=event_type)

        return events

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['event_type'] = self.request.GET.get('event_type', '')
        context['event_type_choices'] = Event.EVENT_TYPE  # Passing EVENT_TYPE choices to the template
        return context

    
# class DashboardView(TemplateView):
#     template_name = 'dashboard.html'pytho

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         status_counts = Event.objects.values('status').annotate(count=Count('status'))
#         context['status_counts'] = status_counts
#         return context
