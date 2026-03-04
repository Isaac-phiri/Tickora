# urls.py
from django.urls import path
from . import views


urlpatterns = [

    path('book/<int:event_id>/', views.EventBookingView.as_view(), name='event_booking'),
    path('confirmation/<str:booking_reference>/', views.booking_confirmation, name='booking_confirmation'),
    path('download-ticket/<int:ticket_id>/', views.download_ticket, name='download_ticket'),
    path('download-all/<str:booking_reference>/', views.download_all_tickets, name='download_all_tickets'),
    
    # path('event/<int:event_id>/', EventBookingView.as_view(), name='event_booking'),
    
    # path('tickets/', TicketListView.as_view(), name='ticket-list'),
    # path('tickets/<int:pk>/', TicketDetailView.as_view(), name='ticket-detail'),
    # path('tickets/<int:pk>/update/', TicketUpdateView.as_view(), name='ticket-update'),
    # path('tickets/<int:pk>/delete/', TicketDeleteView.as_view(), name='ticket-delete'),
    # path('tickets/status/<str:status>/', TicketStatusListView.as_view(), name='ticket-status-list'),

  
]
