from django import forms
from django.utils.text import slugify
from django.utils import timezone
from .models import Event
from tickets.models import TicketType
from django.forms import inlineformset_factory
from decimal import Decimal


class EventForm(forms.ModelForm):
    """
    Form for creating and editing events
    """
    class Meta:
        model = Event
        fields = [
            'title', 'slug', 'description', 'short_description',
            'start_date', 'end_date', 'door_open_time',
            'venue_name', 'venue_type', 'address_line1', 'address_line2',
            'city', 'state', 'country', 'postal_code',
            'latitude', 'longitude',
            'virtual_meeting_url', 'virtual_meeting_password',
            'banner_image', 'thumbnail_image',
            'status', 'is_featured', 'is_private', 'invitation_code',
            'max_capacity', 'min_age_requirement',
            'co_organizers', 'tags', 'terms_and_conditions', 'refund_policy'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'short_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'door_open_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'venue_name': forms.TextInput(attrs={'class': 'form-control'}),
            'venue_type': forms.Select(attrs={'class': 'form-select'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'virtual_meeting_url': forms.URLInput(attrs={'class': 'form-control'}),
            'virtual_meeting_password': forms.TextInput(attrs={'class': 'form-control'}),
            'banner_image': forms.FileInput(attrs={'class': 'form-control'}),
            'thumbnail_image': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'invitation_code': forms.TextInput(attrs={'class': 'form-control'}),
            'max_capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'min_age_requirement': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'co_organizers': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Comma separated tags'}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'refund_policy': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if not slug:
            slug = slugify(self.cleaned_data.get('title', ''))
        
        # Check uniqueness
        qs = Event.objects.filter(slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise forms.ValidationError("This slug is already in use. Please choose another.")
        
        return slug

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError("End date must be after start date.")
        
        if start_date and start_date < timezone.now():
            raise forms.ValidationError("Start date cannot be in the past.")
        
        return cleaned_data


class TicketTypeForm(forms.ModelForm):
    """
    Form for creating ticket types within an event
    """
    class Meta:
        model = TicketType
        fields = [
            'name', 'ticket_class', 'description',
            'price', 'early_bird_price', 'early_bird_end_date',
            'quantity_available', 'max_per_order', 'min_per_order',
            'sales_start_date', 'sales_end_date',
            'service_fee_percentage', 'service_fee_fixed'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'ticket_class': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'early_bird_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'early_bird_end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'quantity_available': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'max_per_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'min_per_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'sales_start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'sales_end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'service_fee_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'service_fee_fixed': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        sales_start = cleaned_data.get('sales_start_date')
        sales_end = cleaned_data.get('sales_end_date')
        early_bird_end = cleaned_data.get('early_bird_end_date')
        
        if sales_start and sales_end and sales_start >= sales_end:
            raise forms.ValidationError("Sales end date must be after sales start date.")
        
        if early_bird_end and sales_end and early_bird_end > sales_end:
            raise forms.ValidationError("Early bird end date must be before sales end date.")
        
        return cleaned_data


# Formset for ticket types
TicketTypeFormSet = inlineformset_factory(
    Event,
    TicketType,
    form=TicketTypeForm,
    extra=1,
    can_delete=True
)


class EventFilterForm(forms.Form):
    """
    Form for filtering events on the frontend
    """
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Search events...'
    }))
    
    city = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'City'
    }))
    
    venue_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Venues')] + list(Event.VenueType.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    price_min = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min Price'})
    )
    
    price_max = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max Price'})
    )
    
    is_featured = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input'
    }))