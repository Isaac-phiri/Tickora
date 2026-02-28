# from django.shortcuts import render, redirect
# from django.urls import reverse_lazy
# from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
# from django.db.models import Q
# from .models import *
# from .forms import *
# from events.managers import TicketManager
# from django.contrib.auth.mixins import LoginRequiredMixin
# from django.contrib.auth.decorators import login_required
# from django.utils.decorators import method_decorator
# from tickets.models import Ticket
# from datetime import timedelta
# from django.shortcuts import get_object_or_404
# from django.utils import timezone



# class EventListView(ListView):
#     model = Event
#     template_name = 'event/event_list.html'
#     context_object_name = 'events'
#     paginate_by = 6

# # class EventHomePageListView(ListView):
# #     model = Event
# #     template_name = 'home/homepage.html'
# #     login_url = 'login'
# #     paginate_by = 4

# #     def get_context_data(self, **kwargs):
# #         context = super().get_context_data(**kwargs)
# #         context["events_list"] = Event.objects.all().order_by('-timestamp') 
# #         context['events'] = Event.objects.all()
# #         context['latest'] = Event.get_latest_events()
# #         return context


# class EventHomePageListView(TemplateView):
#     template_name = 'home/homepage.html'
#     paginate_by = 6  # Items per page

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
        
#         # Get the type parameter from URL
#         listing_type = self.request.GET.get('type', 'cinema')
        
#         # Cinema listing
#         cinema_list = Cinema.objects.filter(is_active=True).order_by('name')
#         cinema_paginator = Paginator(cinema_list, self.paginate_by)
#         cinema_page = self.request.GET.get('cinema_page', 1)
#         context['cinemas'] = cinema_paginator.get_page(cinema_page)

        
        
#         # Event listing
#         event_list = Event.objects.all().order_by('-timestamp')
#         event_paginator = Paginator(event_list, self.paginate_by)
#         event_page = self.request.GET.get('event_page', 1)
#         context['events_list'] = event_paginator.get_page(event_page)
#         context['events'] = Event.objects.all()
#         context['latest'] = Event.get_latest_events()
        
#         # Pass the active tab type
#         context['active_tab'] = listing_type
        
#         return context

    
# # class LatestEventListView(ListView):
# #     model = Event
# #     template_name = 'home/homepage.html'
# #     context_object_name = 'latest_events'

# #     def get_context_data(self, **kwargs):
# #         context = super().get_context_data(**kwargs)
# #         context['latest_events'] = Event.objects.latest_events(limit=5)
# #         return context


# # @method_decorator(login_required, name='dispatch')
# class EventDetailView(DetailView):
#     model = Event
#     template_name = 'event/event_detail.html'
#     context_object_name = 'event'
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         event = self.get_object()
        
#         # Get distinct ticket types for this event
#         ticket_types = Ticket.objects.filter(event=event).values_list("ticket_type", flat=True).distinct()
        
#         context['ticket_types'] = ticket_types  
#         return context
    
# # @method_decorator(login_required, name='dispatch')
# class EventCreateView(CreateView):
#     model = Event
#     form_class = EventForm
#     template_name = 'events/event_form.html'
#     success_url = reverse_lazy('event-list')
    

# class EventUpdateView(UpdateView):
#     model = Event
#     form_class = EventForm
#     template_name = 'events/event_form.html'
#     success_url = reverse_lazy('event-list')

# class EventDeleteView(DeleteView):
#     model = Event
#     template_name = 'events/event_confirm_delete.html'
#     success_url = reverse_lazy('event-list')

# class EventStatusListView(ListView):
#     model = Event
#     template_name = 'events/event_status_list.html'
#     context_object_name = 'events'

#     def get_queryset(self):
#         status = self.kwargs.get('status')
#         return Event.objects.filter(status=status)


# class EventSearchListView(ListView):
#     template_name = 'event/event_list.html'
#     context_object_name = 'events'

#     def get_queryset(self):
#         query = self.request.GET.get('q')
#         event_type = self.request.GET.get('event_type', None)
        
#         # Start with all active events
#         events = Event.objects.filter(status='Active')
        
#         # Filter by search query
#         if query:
#             events = events.filter(
#                 Q(event_name__icontains=query) | 
#                 Q(description__icontains=query)
#             )
        
#         # Filter by event type
#         if event_type:
#             events = events.filter(event_type=event_type)

#         return events

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['search_query'] = self.request.GET.get('q', '')
#         context['event_type'] = self.request.GET.get('event_type', '')
#         context['event_type_choices'] = Event.EVENT_TYPE  # Passing EVENT_TYPE choices to the template
#         return context

    
# # class DashboardView(TemplateView):
# #     template_name = 'dashboard.html'pytho

# #     def get_context_data(self, **kwargs):
# #         context = super().get_context_data(**kwargs)
# #         status_counts = Event.objects.values('status').annotate(count=Count('status'))
# #         context['status_counts'] = status_counts
# #         return context

# class AirlineTicketListView(ListView):
#     model = AirlineTicket
#     template_name = 'airline_ticket_list.html'
#     context_object_name = 'airline_tickets'

# class AirlineTicketDetailView(DetailView):
#     model = AirlineTicket
#     template_name = 'airline_ticket_detail.html'
#     context_object_name = 'airline_ticket'

# class AirlineTicketCreateView(CreateView):
#     model = AirlineTicket
#     form_class = AirlineTicketForm
#     template_name = 'airline_ticket_form.html'
#     success_url = reverse_lazy('airline_ticket_list')

# class AirlineTicketUpdateView(UpdateView):
#     model = AirlineTicket
#     form_class = AirlineTicketForm
#     template_name = 'airline_ticket_form.html'
#     success_url = reverse_lazy('airline_ticket_list')

# class AirlineTicketDeleteView(DeleteView):
#     model = AirlineTicket
#     template_name = 'airline_ticket_confirm_delete.html'
#     success_url = reverse_lazy('airline_ticket_list')
    



# class CinemaListView(ListView):
#     model = Cinema
#     template_name = 'cinema/cinema_list.html'
#     context_object_name = 'cinemas'
#     paginate_by = 10
    
#     def get_queryset(self):
#         return Cinema.objects.filter(is_active=True).order_by('name')

# class CinemaDetailView(TemplateView):
#     template_name = 'cinema/cinema_detail.html'
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         cinema = get_object_or_404(Cinema, id=self.kwargs['pk'], is_active=True)
        
#         # Get dates for display (today + next 7 days)
#         today = timezone.now().date()
#         upcoming_dates = (today + timedelta(days=7)).strftime("%B %d")
        
#         # Movies currently showing at this cinema
#         now_showing_movies = Movie.objects.filter(
#             is_active=True,
#             screenings__cinema=cinema,
#             screenings__start_time__gte=timezone.now(),
#             release_date__lte=today
#         ).distinct().prefetch_related('screenings', 'genre')
        
#         # Coming soon movies
#         coming_soon_movies = Movie.objects.filter(
#             is_active=True,
#             screenings__cinema=cinema,
#             release_date__gt=today
#         ).distinct().order_by('release_date')[:5]
        
#         context.update({
#             'cinema': cinema,
#             'now_showing_movies': now_showing_movies,
#             'coming_soon_movies': coming_soon_movies,
#             'upcoming_dates': upcoming_dates,
#         })
#         return context

# class MovieListView(ListView):
#     model = Movie
#     template_name = 'movies/movie_list.html'
#     context_object_name = 'movies'
#     paginate_by = 12
    
#     def get_queryset(self):
#         return Movie.objects.filter(is_active=True).order_by('-release_date')

# class MovieDetailView(DetailView):
#     model = Movie
#     template_name = 'movies/movie_detail.html'
#     context_object_name = 'movie'
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['upcoming_screenings'] = Screening.objects.filter(
#             movie=self.object,
#             start_time__gte=timezone.now()
#         ).order_by('start_time')[:10]
#         return context

# def home(request):
#     now_showing = Movie.objects.filter(
#         is_active=True,
#         release_date__lte=timezone.now(),
#         end_date__gte=timezone.now()
#     )[:6]
    
#     coming_soon = Movie.objects.filter(
#         is_active=True,
#         release_date__gt=timezone.now()
#     )[:4]
    
#     featured_cinemas = Cinema.objects.filter(is_active=True)[:4]
    
#     return render(request, 'cinema/home.html', {
#         'now_showing': now_showing,
#         'coming_soon': coming_soon,
#         'featured_cinemas': featured_cinemas,
#     })

 
    
# class BusTicketListView(ListView):
#     model = BusTicket
#     template_name = 'bus_ticket_list.html'
#     context_object_name = 'bus_tickets'

# class BusTicketDetailView(DetailView):
#     model = BusTicket
#     template_name = 'bus_ticket_detail.html'
#     context_object_name = 'bus_ticket'

# class BusTicketCreateView(CreateView):
#     model = BusTicket
#     form_class = BusTicketForm
#     template_name = 'bus_ticket_form.html'
#     success_url = reverse_lazy('bus_ticket_list')

# class BusTicketUpdateView(UpdateView):
#     model = BusTicket
#     form_class = BusTicketForm
#     template_name = 'bus_ticket_form.html'
#     success_url = reverse_lazy('bus_ticket_list')

# class BusTicketDeleteView(DeleteView):
#     model = BusTicket
#     template_name = 'bus_ticket_confirm_delete.html'
#     success_url = reverse_lazy('bus_ticket_list')

