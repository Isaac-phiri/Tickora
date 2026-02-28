# forms.py
from django import forms
from .models import Event, AirlineTicket, CinemaTicket, BusTicket
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'organizer', 'image', 'event_name', 'description', 
            'date_and_time', 'venue', 'status'
        ]

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save Event'))

class AirlineTicketForm(forms.ModelForm):
    class Meta:
        model = AirlineTicket
        fields = '__all__'

class CinemaTicketForm(forms.ModelForm):
    class Meta:
        model = CinemaTicket
        fields = '__all__'

class BusTicketForm(forms.ModelForm):
    class Meta:
        model = BusTicket
        fields = '__all__'
