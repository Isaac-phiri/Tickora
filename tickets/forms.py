# forms.py
from django import forms
from .models import Ticket
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            'event', 'ticket_type', 'quantity', 
            'sales_end_date', 'sales_status'
        ]

    def __init__(self, *args, **kwargs):
        super(TicketForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Save Ticket'))
