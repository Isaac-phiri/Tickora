# managers.py
from django.db import models
from .models import *
from django.db.models import Q
from django.utils import timezone


class TicketManager(models.Manager):
    def get_all_tickets(self, date_and_time=None, max_price=None):
        query = Q()
        if date_and_time:
            query &= Q(date_and_time__gte=date_and_time) | Q(departure_time__gte=date_and_time) | Q(screening_time__gte=date_and_time)
        if max_price:
            query &= Q(price__lte=max_price)
        
        event_tickets = Event.objects.filter(query)
        airline_tickets = AirlineTicket.objects.filter(query)
        cinema_tickets = CinemaTicket.objects.filter(query)
        bus_tickets = BusTicket.objects.filter(query)

        return {
            'event_tickets': event_tickets,
            'airline_tickets': airline_tickets,
            'cinema_tickets': cinema_tickets,
            'bus_tickets': bus_tickets,
        }
