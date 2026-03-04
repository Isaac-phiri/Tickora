from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import User


@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """
    Send welcome email to new users
    """
    if created and instance.email:
        subject = 'Welcome to Ticketing System'
        message = f"""
        Hi {instance.first_name},
        
        Welcome to our Ticketing System! We're excited to have you on board.
        
        You can now browse events and purchase tickets.
        
        Best regards,
        The Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.email],
            fail_silently=True,
        )