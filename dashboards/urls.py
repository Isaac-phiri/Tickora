from django.urls import path
from .views import *

urlpatterns = [
     path('dashboard/', DashboardHomeView.as_view(), name='dashboard'),
]
