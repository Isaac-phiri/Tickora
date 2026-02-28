from django.urls import path
from .views import *

urlpatterns = [

    # path('payment/', PaymentView.as_view(), name='payment_page'),
    # path('callback/', payment_callback, name='payment_callback'),
    # path('success/<str:ticket_id>/', payment_success, name='payment_success'),
    # path('payment_failed/<str:ticket_id>/', PaymentFailedView.as_view(), name='payment_failed'),

    # path('payments/success/<int:ticket_id>/', payment_success, name='payment_success'),
    # path('payments/cancel/', payment_cancel, name='payment_cancel'),

    # path('airtel/collection/txnEnquiry/<str:transaction_id>/', check_transaction_status, name='check_transaction_status'),
]
