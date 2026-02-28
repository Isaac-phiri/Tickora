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
            return redirect('homepage')  # Ensure this matches your URL pattern name
        else:
            print("Authentication failed")
            return render(request, 'registration/login.html', {'error': 'Invalid credentials'})
    return render(request, 'registration/login.html')


def logout_view(request):
    logout(request)
    return redirect(reverse('homepage'))


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