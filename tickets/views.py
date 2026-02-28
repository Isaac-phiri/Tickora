# # views.py
# from django.urls import reverse_lazy
# from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
# from .models import Ticket
# from .forms import TicketForm
# from django.db.models import Count
# from events.models import Event
# from django.shortcuts import get_object_or_404, redirect, render
# import random
# import string
# from orders.models import Order
# from django.urls import reverse
# from accounts.models import User
# from django.views import View
# from django.shortcuts import render
# from django.http import JsonResponse
# from tickets.models import Ticket
# from django.core.mail import send_mail
# from django.conf import settings
# from django.core.mail import send_mail
# from django.template.loader import render_to_string
# from django.views import View
# from django.views.decorators.csrf import csrf_exempt
# from django.shortcuts import render, redirect, get_object_or_404
# from django.http import HttpResponse
# from django.conf import settings
# from django.template.loader import render_to_string
# from django.utils.html import strip_tags
# from django.core.mail import send_mail
# from django.contrib.auth import login

# import logging
# from .models import Ticket  # your Ticket model
# logger = logging.getLogger(__name__)


# def send_ticket_email(ticket):
#     subject = f"Your Ticket for {ticket.event.event_name}"
#     recipient_email = ticket.user.email

#     email_html_content = render_to_string('emails/ticket_email.html', {'ticket': ticket})
#     email_plain_text = strip_tags(email_html_content)

#     try:
#         send_mail(
#             subject,
#             email_plain_text,
#             settings.DEFAULT_FROM_EMAIL,
#             [recipient_email],
#             html_message=email_html_content,
#             fail_silently=False,
#         )
#         logger.info(f"Ticket email sent successfully to {recipient_email}")
#     except Exception as e:
#         logger.error(f"Failed to send ticket email: {str(e)}")



# # class EventBookingView(View):
# #     def get(self, request, event_id):
# #         event = Event.objects.get(id=event_id)
# #         return render(request, 'event_detail.html', {'event': event})

# #     def post(self, request, event_id):
# #         # Step 1: Process form data from event detail page
# #         event = Event.objects.get(id=event_id)
# #         ticket_type = request.POST.get('ticket_type')
# #         quantity = int(request.POST.get('quantity', 1))
        
# #         # Create ticket (but don't save yet)
# #         ticket = Ticket(
# #             event=event,
# #             user=request.user,
# #             ticket_type=ticket_type,
# #             quantity=quantity,
# #             total_price=event.price * quantity
# #         )
# #         ticket.save()  # This will generate the ticket_id
        
# #         # Store ticket ID in session for payment step
# #         request.session['current_ticket_id'] = ticket.ticket_id
        
# #         # Redirect to payment page
# #         return redirect('payment_page')

# class EventBookingView(View):
#     def get(self, request, event_id):
#         event = Event.objects.get(id=event_id)
#         return render(request, 'event_detail.html', {'event': event})

#     def post(self, request, event_id):
#         event = Event.objects.get(id=event_id)
#         name = request.POST.get('name')
#         price = request.POST.get('price')
#         email = request.POST.get('email')
#         phone_number = request.POST.get('phone_number')

#         # If user is not authenticated, create an account for them
#         if not request.user.is_authenticated:
#             # Check if user with this email already exists
#             try:
#                 user = User.objects.get(email=email)
#             except User.DoesNotExist:
#                 # Generate a random password
#                 password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                
#                 # Split full name into first and last names
#                 name_parts = full_name.split(' ')
#                 first_name = name_parts[0]
#                 last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                
#                 # Create the user
#                 user = User.objects.create_user(
#                     email=email,
#                     first_name=first_name,
#                     last_name=last_name,
#                     phone_number=phone_number,
#                     password=password
#                 )
                
#                 # Automatically log in the new user
#                 login(request, user)
                
#                 # Here you might want to send the generated password to the user's email
#                 # send_welcome_email(user.email, password)

#         else:
#             user = request.user

#         # Create and save the ticket
#         ticket = Ticket(
#             event=event,
#             user=user,
#             ticket_type=ticket_type,
#             quantity=quantity,
#             total_price=event.price * quantity
#         )
#         ticket.save()

#         # Store ticket ID in session for payment step
#         request.session['current_ticket_id'] = ticket.ticket_id

#         # Redirect to payment page
#         return redirect('payment_page')


# class TicketListView(ListView):
#     model = Ticket
#     template_name = 'tickets/ticket_list.html'
#     context_object_name = 'tickets'

# class TicketDetailView(DetailView):
#     model = Ticket
#     template_name = 'tickets/ticket_detail.html'
#     context_object_name = 'ticket'

# # class TicketCreateView(CreateView):
# #     model = Ticket
# #     form_class = TicketForm
# #     template_name = 'tickets/ticket_form.html'
# #     success_url = reverse_lazy('ticket-list')

# # @login_required
# # def create_ticket(request, event_id):
# #     event = get_object_or_404(Event, id=event_id)

# #     if event.tickets_available() <= 0:
# #         return redirect('event_detail', event_id=event_id)

# #     # Create the ticket
# #     ticket = Ticket.objects.create(
# #         event=event,
# #         user=request.user,
# #         ticket_type='General Admission',  # or based on user selection
# #         quantity=1,
# #         total_price=event.price,
# #         sales_status='Available'
# #     )

# #     # Redirect to payment page
# #     return redirect(reverse('make_payment', kwargs={'ticket_id': ticket.id}))



# class TicketUpdateView(UpdateView):
#     model = Ticket
#     form_class = TicketForm
#     template_name = 'tickets/ticket_form.html'
#     success_url = reverse_lazy('ticket-list')

# class TicketDeleteView(DeleteView):
#     model = Ticket
#     template_name = 'tickets/ticket_confirm_delete.html'
#     success_url = reverse_lazy('ticket-list')
    
# class DashboardView(TemplateView):
#     template_name = 'dashboard.html'

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         status_counts = Ticket.objects.values('sales_status').annotate(count=Count('sales_status'))
#         context['ticket_status_counts'] = status_counts
#         return context


# class TicketStatusListView(ListView):
#     model = Ticket
#     template_name = 'tickets/ticket_status_list.html'
#     context_object_name = 'tickets'

#     def get_queryset(self):
#         status = self.kwargs.get('status')
#         return Ticket.objects.filter(sales_status=status)
