from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [

    path('pay/<int:order_id>/', views.PaymentView.as_view(), name='payment_page'),
    path('callback/', views.PaymentCallbackView.as_view(), name='payment_callback'),
    path('ipn/', views.PaymentIPNView.as_view(), name='payment_ipn'),
    path('status/<int:order_id>/', views.payment_status_check, name='payment_status_check'),
    path('retry/<int:order_id>/', views.payment_retry, name='payment_retry'),
    path('payments/failed/<int:order_id>/', views.PaymentFailedView.as_view(), name='payment_failed'),  

    # Payment processing
    path('process/<int:order_id>/', views.payment_process, name='process'),
    path('success/<int:order_id>/', views.payment_success, name='success'),
    path('cancel/<int:order_id>/', views.payment_cancel, name='cancel'),

     # Payment success/cancel
    path('success/<int:order_id>/', views.payment_success, name='payment_success'),
    path('cancel/<int:order_id>/', views.payment_cancel, name='payment_cancel'),
    
    # Webhook (no CSRF token needed)
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    
    # Dashboard URLs (Admin only)
    path('dashboard/payments/', views.dashboard_payment_list, name='dashboard_payment_list'),
]