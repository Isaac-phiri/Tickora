from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import UserCreationForm, UserChangeForm
from .models import * 

class UserAdmin(admin.ModelAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    list_display = ['email', 'first_name', 'last_name', 'user_type', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']
    list_filter = ['user_type', 'is_active']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Contact Info', {'fields': ('phone_number', 'profile_pic')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('date_joined',)}),
    )
    readonly_fields = ('date_joined',)
    filter_horizontal = ()
    ordering = ('email',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )

admin.site.register(User, UserAdmin)

class BaseModelAdmin(admin.ModelAdmin):
    """Base admin class with common functionality"""
    
    readonly_fields = ['created_at', 'updated_at']
    model = BaseModel
    
    def get_list_display(self, request):
        """Add created_at to list display if not specified"""
        list_display = super().get_list_display(request)
        if 'created_at' not in list_display:
            list_display = list(list_display) + ['created_at']
        return list_display
    
    def get_queryset(self, request):
        """Exclude inactive items by default unless explicitly requested"""
        queryset = super().get_queryset(request)
        
        # Check if we should show inactive items
        if request.GET.get('show_inactive') != '1':
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    def inactive_filter(self, request):
        """Add filter for active/inactive in changelist"""
        from django.contrib.admin import SimpleListFilter
        
        class ActiveFilter(SimpleListFilter):
            title = 'active status'
            parameter_name = 'active'
            
            def lookups(self, request, model_admin):
                return (
                    ('active', 'Active only'),
                    ('inactive', 'Inactive only'),
                    ('all', 'All'),
                )
            
            def queryset(self, request, queryset):
                if self.value() == 'inactive':
                    return queryset.filter(is_active=False)
                elif self.value() == 'active':
                    return queryset.filter(is_active=True)
                return queryset
        
        return ActiveFilter
    
    actions = ['soft_delete_selected', 'restore_selected']
    
    def soft_delete_selected(self, request, queryset):
        """Soft delete selected items"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} items soft deleted.")
    soft_delete_selected.short_description = "Soft delete selected items"
    
    def restore_selected(self, request, queryset):
        """Restore soft deleted items"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} items restored.")
    restore_selected.short_description = "Restore selected items"
