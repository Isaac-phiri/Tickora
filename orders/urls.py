from django.urls import path
from . import views
from .order_dashboard import (
    OrderListView, OrderDetailView, OrderStatusUpdateView, OrderExportView
)

app_name = 'orders'

urlpatterns = [
    # Cart URLs
    path('checkout/<int:event_id>/', views.checkout, name='checkout'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:ticket_type_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:ticket_type_id>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:ticket_type_id>/', views.cart_remove, name='cart_remove'),
    
    # Checkout URLs
    path('checkout/', views.checkout_view, name='checkout'),
    
    # Order URLs (Public)
    path('history/', views.order_history, name='order_history'),
    path('confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('<int:order_id>/tickets/', views.order_tickets, name='order_tickets'),
    
    # Dashboard URLs (Staff/Admin)
    # path('dashboard/orders/', views.dashboard_order_list, name='dashboard_order_list'),
    # path('dashboard/orders/<int:pk>/', views.dashboard_order_detail, name='dashboard_order_detail'),
    # path('dashboard/orders/<int:pk>/update-status/', views.dashboard_order_update_status, name='dashboard_order_update_status'),
    
    path('orders/', OrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/status/', OrderStatusUpdateView.as_view(), name='order_status_update'),
    path('orders/export/', OrderExportView.as_view(), name='order_export'),
]