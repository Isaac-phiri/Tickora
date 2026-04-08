# views/user_management.py
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404, redirect

from accounts.models import User
from orders.models import Order
from payments.models import Payment


class AdminUserRequiredMixin(UserPassesTestMixin):
    """Mixin for admin-only user management"""
    
    def test_func(self):
        return self.request.user.user_type == 'Admin' or self.request.user.is_superuser


class UserListView(AdminUserRequiredMixin, ListView):
    """List all users (admin only)"""
    model = User
    template_name = 'dashboard/users/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = User.objects.all()
        
        # Apply filters
        user_type = self.request.GET.get('user_type')
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        
        is_active = self.request.GET.get('is_active')
        if is_active == 'active':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone_number__icontains=search)
            )
        
        return queryset.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # User statistics
        context['stats'] = {
            'total': User.objects.count(),
            'admin': User.objects.filter(user_type='Admin').count(),
            'staff': User.objects.filter(user_type='Staff').count(),
            'customer': User.objects.filter(user_type='Customer').count(),
            'active': User.objects.filter(is_active=True).count(),
            'inactive': User.objects.filter(is_active=False).count(),
        }
        
        context['user_type_choices'] = User.USER_TYPE
        context['current_user_type'] = self.request.GET.get('user_type', '')
        context['active_filter'] = self.request.GET.get('is_active', '')
        context['search_query'] = self.request.GET.get('search', '')
        
        return context


class UserDetailView(AdminUserRequiredMixin, DetailView):
    """Detailed view of a user with analytics"""
    model = User
    template_name = 'dashboard/users/user_detail.html'
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        # Order statistics
        orders = Order.objects.filter(user=user)
        paid_orders = orders.filter(status=Order.OrderStatus.PAID)
        
        # Payment statistics
        payments = Payment.objects.filter(user=user, status=Payment.PaymentStatus.COMPLETED)
        
        context['stats'] = {
            'total_orders': orders.count(),
            'completed_orders': paid_orders.count(),
            'total_spent': payments.aggregate(total=Sum('amount'))['total'] or 0,
            'total_tickets': sum(order.ticket_count for order in paid_orders),
        }
        
        # Recent orders
        context['recent_orders'] = orders.select_related('event').order_by('-order_date')[:10]
        
        # Recent payments
        context['recent_payments'] = payments.select_related('order').order_by('-payment_date')[:10]
        
        return context


class UserCreateView(AdminUserRequiredMixin, CreateView):
    """Create a new user (admin only)"""
    model = User
    template_name = 'dashboard/users/user_form.html'
    fields = [
        'email', 'first_name', 'last_name', 'phone_number',
        'user_type', 'profile_pic', 'is_active', 'is_staff'
    ]
    
    def form_valid(self, form):
        # Set a default password that user must change
        form.instance.set_password(User.objects.make_random_password())
        response = super().form_valid(form)
        messages.success(self.request, f'User {self.object.email} created successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New User'
        context['is_create'] = True
        return context
    
    def get_success_url(self):
        return reverse_lazy('dashboard:user_list')


class UserUpdateView(AdminUserRequiredMixin, UpdateView):
    """Update user information"""
    model = User
    template_name = 'dashboard/users/user_form.html'
    fields = [
        'email', 'first_name', 'last_name', 'phone_number',
        'user_type', 'profile_pic', 'is_active', 'is_staff', 'is_superuser'
    ]
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'User {self.object.email} updated successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit User: {self.object.email}'
        context['is_create'] = False
        return context
    
    def get_success_url(self):
        return reverse_lazy('dashboard:user_list')


class UserPasswordResetView(AdminUserRequiredMixin, UpdateView):
    """Reset user password"""
    model = User
    fields = []
    template_name = 'dashboard/users/user_password_reset.html'
    
    def form_valid(self, form):
        new_password = User.objects.make_random_password()
        self.object.set_password(new_password)
        self.object.save()
        
        messages.success(
            self.request,
            f'Password reset for {self.object.email}. New password: {new_password}'
        )
        
        return redirect('dashboard:user_detail', pk=self.object.pk)
    
    def get_success_url(self):
        return reverse_lazy('dashboard:user_detail', kwargs={'pk': self.object.pk})