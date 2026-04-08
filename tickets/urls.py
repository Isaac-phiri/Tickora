# urls.py
from django.urls import path
from . import views
from .ticket_dashboard import (
    TicketTypeListView, TicketTypeCreateView, TicketTypeUpdateView,
    TicketListView, TicketDetailView, TicketCheckInView,
    BulkTicketCheckInView, TicketExportView
)


urlpatterns = [

    path('book/<int:event_id>/', views.EventBookingView.as_view(), name='event_booking'),
    path('confirmation/<str:booking_reference>/', views.booking_confirmation, name='booking_confirmation'),
    path('download-ticket/<int:ticket_id>/', views.download_ticket, name='download_ticket'),
    path('download-all/<str:booking_reference>/', views.download_all_tickets, name='download_all_tickets'),
    
    path('events/<int:event_id>/ticket-types/', TicketTypeListView.as_view(), name='ticket_type_list'),
    path('events/<int:event_id>/ticket-types/create/', TicketTypeCreateView.as_view(), name='ticket_type_create'),
    path('ticket-types/<int:pk>/edit/', TicketTypeUpdateView.as_view(), name='ticket_type_edit'),
    
    # Ticket Management
    path('tickets/', TicketListView.as_view(), name='ticket_list'),
    path('events/<int:event_id>/tickets/', TicketListView.as_view(), name='event_ticket_list'),
    path('tickets/<int:pk>/', TicketDetailView.as_view(), name='ticket_detail'),
    path('tickets/<int:pk>/check-in/', TicketCheckInView.as_view(), name='ticket_check_in'),
    path('events/<int:event_id>/bulk-checkin/', BulkTicketCheckInView.as_view(), name='bulk_checkin'),
    path('events/<int:event_id>/tickets/export/', TicketExportView.as_view(), name='ticket_export'),
    
    # path('event/<int:event_id>/', EventBookingView.as_view(), name='event_booking'),
    
    # path('tickets/', TicketListView.as_view(), name='ticket-list'),
    # path('tickets/<int:pk>/', TicketDetailView.as_view(), name='ticket-detail'),
    # path('tickets/<int:pk>/update/', TicketUpdateView.as_view(), name='ticket-update'),
    # path('tickets/<int:pk>/delete/', TicketDeleteView.as_view(), name='ticket-delete'),
    # path('tickets/status/<str:status>/', TicketStatusListView.as_view(), name='ticket-status-list'),

  
]
