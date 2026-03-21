from django.urls import path
from .views import *

app_name = 'events'

urlpatterns = [
     
    path('', EventHomePageListView.as_view(), name="homepage"),

    path('event_list/', EventListView.as_view(), name='event-list'),
    path('event_detail/<int:pk>/', EventDetailView.as_view(), name='event-detail'),
    path('event_create/', EventCreateView.as_view(), name='event-create'),
    path('event_update/<int:pk>/', EventUpdateView.as_view(), name='event-update'),
    path('event_delete/<int:pk>/', EventDeleteView.as_view(), name='event-delete'),
    path('status/<str:status>/', EventStatusListView.as_view(), name='event-status-list'),
    path('event_search/', EventSearchListView.as_view(), name='event_search'),


    path('about-us/', AboutUsView.as_view(), name='about_us'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('services/', ServicesView.as_view(), name='services'),
]
