# urls.py
from django.urls import path
from .views import TransactionListView, TransactionDetailView, TransactionStatusListView

urlpatterns = [
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction-detail'),
    path('transactions/status/<str:status>/', TransactionStatusListView.as_view(), name='transaction-status-list'),
]
