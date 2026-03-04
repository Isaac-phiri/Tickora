from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path("signup/", create_user ,name="signup"),
    path("login/", login_view ,name="login"),
    path('logout/', logout_view,  name='logout'),
    path('contact/', contact_us, name='contact_us'),

    # Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard/customer/', customer_dashboard, name='customer_dashboard'),
    path('dashboard/staff/', staff_dashboard, name='staff_dashboard'),
    path('dashboard/admin/', admin_dashboard, name='admin_dashboard'),
    
    # Profile
    path('profile/', profile_view, name='profile'),
    
    # Admin User Management
    path('admin/users/', user_list, name='user_list'),
    path('admin/users/create/', user_create, name='user_create'),
    path('admin/users/<int:pk>/edit/', user_edit, name='user_edit'),
    path('admin/users/<int:pk>/toggle-active/', user_toggle_active, name='user_toggle_active'),
    path('admin/users/<int:pk>/', user_detail, name='user_detail'),

]

