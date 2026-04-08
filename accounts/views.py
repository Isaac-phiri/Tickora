from django.shortcuts import render
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from .forms import *
from django.contrib import messages
from django.views.generic import ListView , DetailView ,View,TemplateView, DeleteView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.contrib.auth import authenticate, login as auth_login
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import User
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, 
    UserProfileForm, AdminUserCreationForm
)
from .decorators import admin_required, staff_required
from events.models import Event
from orders.models import Order
from tickets.models import Ticket


def create_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            email = form.cleaned_data.get('email')
            raw_password = form.cleaned_data.get('password1')  # Use password1 field
            user = authenticate(email=email, password=raw_password)
            if user is not None:
                login(request, user)
                return redirect('login')
            else:
                # Debugging: print error message if authentication fails
                print("User authentication failed.")
        else:
            # Debugging: print form errors if form is not valissd
            print(form.errors)
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            print("User authenticated:", user)
            auth_login(request, user)
            return redirect('events:homepage')  # Ensure this matches your URL pattern name
        else:
            print("Authentication failed")
            return render(request, 'registration/login.html', {'error': 'Invalid credentials'})
    return render(request, 'registration/login.html')


def logout_view(request):
    logout(request)
    return redirect(reverse('events:homepage'))


def contact_us(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            message = form.cleaned_data['message']
            
            # Debug: Print out the email components before sending
            print(f"Sending email from: {settings.DEFAULT_FROM_EMAIL}")
            print(f"To: {'iphiri143@gmail.com'}")
            print(f"Subject: Message from {name} ({email})")
            print(f"Message Body:\nPhone: {phone}\nMessage:\n{message}")
            
            try:
                # Sending email
                send_mail(
                    f'Message from {name} ({email})',
                    f'Phone: {phone}\nMessage:\n{message}',
                    settings.DEFAULT_FROM_EMAIL,
                    ['iphiri143@gmail.com'],  # Replace with your recipient email
                    fail_silently=False,
                )
                return render(request, 'home/contact_us_access.html')  # Redirect on success
            except Exception as e:
                # Log the exception or print it for debugging
                print(f"Error occurred while sending email: {e}")
                return render(request, 'home/contact.html', {'form': form, 'error_message': 'There was an error sending your message. Please try again later.'})
    
    else:
        form = ContactForm()

    return render(request, 'home/contact.html', {'form': form})












# def register_view(request):
#     """
#     User registration view
#     """
#     if request.user.is_authenticated:
#         return redirect('accounts:dashboard')
    
#     if request.method == 'POST':
#         form = CustomUserCreationForm(request.POST, request.FILES)
#         if form.is_valid():
#             user = form.save()
#             login(request, user)
#             messages.success(request, f'Welcome {user.first_name}! Your account has been created successfully.')
#             return redirect('accounts:dashboard')
#     else:
#         form = CustomUserCreationForm()
    
#     return render(request, 'accounts/register.html', {'form': form})


# def login_view(request):
#     """
#     User login view
#     """
#     if request.user.is_authenticated:
#         return redirect('accounts:dashboard')
    
#     if request.method == 'POST':
#         form = CustomAuthenticationForm(request, data=request.POST)
#         if form.is_valid():
#             email = form.cleaned_data.get('username')
#             password = form.cleaned_data.get('password')
#             user = authenticate(request, username=email, password=password)
#             if user is not None:
#                 login(request, user)
#                 messages.success(request, f'Welcome back, {user.first_name}!')
#                 next_url = request.GET.get('next', 'accounts:dashboard')
#                 return redirect(next_url)
#     else:
#         form = CustomAuthenticationForm()
    
#     return render(request, 'accounts/login.html', {'form': form})


# def logout_view(request):
#     """
#     User logout view
#     """
#     logout(request)
#     messages.info(request, 'You have been logged out successfully.')
#     return redirect('events:event_list')


# @login_required
# def dashboard_view(request):
#     """
#     Main dashboard view - redirects to appropriate dashboard based on user type
#     """
#     if request.user.user_type == 'Admin':
#         return redirect('accounts:admin_dashboard')
#     elif request.user.user_type == 'Staff':
#         return redirect('accounts:staff_dashboard')
#     else:
#         return redirect('accounts:customer_dashboard')


# @login_required
# def customer_dashboard(request):
#     """
#     Customer dashboard showing their orders and tickets
#     """
#     user = request.user
    
#     # Get user's orders
#     orders = Order.objects.filter(user=user).order_by('-order_date')[:10]
    
#     # Get user's tickets
#     tickets = Ticket.objects.filter(order__user=user).select_related(
#         'event', 'ticket_type'
#     ).order_by('-created_at')[:10]
    
#     # Statistics
#     total_orders = Order.objects.filter(user=user).count()
#     total_tickets = Ticket.objects.filter(order__user=user).count()
#     upcoming_events = Ticket.objects.filter(
#         order__user=user,
#         event__start_date__gte=timezone.now(),
#         status='valid'
#     ).count()
    
#     context = {
#         'orders': orders,
#         'tickets': tickets,
#         'total_orders': total_orders,
#         'total_tickets': total_tickets,
#         'upcoming_events': upcoming_events,
#     }
#     return render(request, 'accounts/dashboard/customer.html', context)


# @login_required
# @staff_required
# def staff_dashboard(request):
#     """
#     Staff dashboard for event management
#     """
#     user = request.user
    
#     # Events managed by staff
#     organized_events = Event.objects.filter(organizer=user).order_by('-start_date')
#     co_organized_events = user.co_organized_events.all().order_by('-start_date')
    
#     # Today's check-ins
#     today = timezone.now().date()
#     today_checkins = Ticket.objects.filter(
#         checked_in_at__date=today,
#         checked_in_by=user
#     ).count()
    
#     # Statistics
#     total_events = organized_events.count() + co_organized_events.count()
#     upcoming_events = Event.objects.filter(
#         Q(organizer=user) | Q(co_organizers=user),
#         start_date__gte=timezone.now(),
#         status='published'
#     ).count()
    
#     context = {
#         'organized_events': organized_events[:5],
#         'co_organized_events': co_organized_events[:5],
#         'today_checkins': today_checkins,
#         'total_events': total_events,
#         'upcoming_events': upcoming_events,
#     }
#     return render(request, 'accounts/dashboard/staff.html', context)


# @login_required
# @admin_required
# def admin_dashboard(request):
#     """
#     Admin dashboard with system-wide statistics
#     """
#     # System statistics
#     total_users = User.objects.count()
#     total_events = Event.objects.count()
#     total_orders = Order.objects.count()
#     total_revenue = Order.objects.filter(status='paid').aggregate(
#         total=Sum('total_amount')
#     )['total'] or 0
    
#     # User breakdown
#     customers = User.objects.filter(user_type='Customer').count()
#     staff = User.objects.filter(user_type='Staff').count()
#     admins = User.objects.filter(user_type='Admin').count()
    
#     # Recent activity
#     recent_orders = Order.objects.select_related('user', 'event').order_by('-order_date')[:10]
#     recent_events = Event.objects.select_related('organizer').order_by('-created_at')[:5]
    
#     # Event status breakdown
#     event_status = Event.objects.values('status').annotate(count=Count('id'))
    
#     context = {
#         'total_users': total_users,
#         'total_events': total_events,
#         'total_orders': total_orders,
#         'total_revenue': total_revenue,
#         'customers': customers,
#         'staff': staff,
#         'admins': admins,
#         'recent_orders': recent_orders,
#         'recent_events': recent_events,
#         'event_status': event_status,
#     }
#     return render(request, 'accounts/dashboard/admin.html', context)


# @login_required
# def profile_view(request):
#     """
#     User profile view and edit
#     """
#     if request.method == 'POST':
#         form = UserProfileForm(request.POST, request.FILES, instance=request.user)
#         if form.is_valid():
#             form.save()
#             messages.success(request, 'Your profile has been updated successfully.')
#             return redirect('accounts:profile')
#     else:
#         form = UserProfileForm(instance=request.user)
    
#     return render(request, 'accounts/profile.html', {'form': form})


# # Admin User Management Views
# @login_required
# @admin_required
# def user_list(request):
#     """
#     Admin view to list all users
#     """
#     users = User.objects.all().order_by('-date_joined')
    
#     # Filter by user type
#     user_type = request.GET.get('user_type')
#     if user_type:
#         users = users.filter(user_type=user_type)
    
#     # Search
#     search = request.GET.get('search')
#     if search:
#         users = users.filter(
#             Q(email__icontains=search) |
#             Q(first_name__icontains=search) |
#             Q(last_name__icontains=search) |
#             Q(phone_number__icontains=search)
#         )
    
#     paginator = Paginator(users, 20)
#     page = request.GET.get('page')
#     users = paginator.get_page(page)
    
#     context = {
#         'users': users,
#         'user_type': user_type,
#         'search': search,
#     }
#     return render(request, 'accounts/dashboard/users/user_list.html', context)


# @login_required
# @admin_required
# def user_create(request):
#     """
#     Admin view to create new user
#     """
#     if request.method == 'POST':
#         form = AdminUserCreationForm(request.POST, request.FILES)
#         if form.is_valid():
#             user = form.save()
#             messages.success(request, f'User {user.email} created successfully.')
#             return redirect('accounts:user_list')
#     else:
#         form = AdminUserCreationForm()
    
#     return render(request, 'accounts/dashboard/users/user_form.html', {'form': form, 'title': 'Create User'})


# @login_required
# @admin_required
# def user_edit(request, pk):
#     """
#     Admin view to edit user
#     """
#     user = get_object_or_404(User, pk=pk)
    
#     if request.method == 'POST':
#         form = CustomUserChangeForm(request.POST, request.FILES, instance=user)
#         if form.is_valid():
#             form.save()
#             messages.success(request, f'User {user.email} updated successfully.')
#             return redirect('accounts:user_list')
#     else:
#         form = CustomUserChangeForm(instance=user)
    
#     return render(request, 'accounts/dashboard/users/user_form.html', {'form': form, 'title': 'Edit User'})


# @login_required
# @admin_required
# @require_POST
# def user_toggle_active(request, pk):
#     """
#     Admin view to toggle user active status
#     """
#     user = get_object_or_404(User, pk=pk)
#     user.is_active = not user.is_active
#     user.save()
    
#     status = 'activated' if user.is_active else 'deactivated'
#     messages.success(request, f'User {user.email} has been {status}.')
    
#     return redirect('accounts:user_list')


# @login_required
# @admin_required
# def user_detail(request, pk):
#     """
#     Admin view to see user details
#     """
#     user = get_object_or_404(User, pk=pk)
    
#     # Get user's orders
#     orders = Order.objects.filter(user=user).order_by('-order_date')
    
#     # Get user's tickets
#     tickets = Ticket.objects.filter(order__user=user).select_related('event', 'ticket_type')
    
#     context = {
#         'profile_user': user,
#         'orders': orders,
#         'tickets': tickets,
#     }
#     return render(request, 'accounts/dashboard/users/user_detail.html', context)