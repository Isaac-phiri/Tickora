# models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.db.models import Q, Sum, F
from django.core.exceptions import ValidationError
from accounts.models import User, BaseModel
from django.apps import apps




class Event(BaseModel):
    """
    Event model representing the main event details
    """
    class EventStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLETED = 'completed', 'Completed'
        SOLD_OUT = 'sold_out', 'Sold Out'

    class VenueType(models.TextChoices):
        INDOOR = 'indoor', 'Indoor'
        OUTDOOR = 'outdoor', 'Outdoor'
        VIRTUAL = 'virtual', 'Virtual'
        HYBRID = 'hybrid', 'Hybrid'

    # Basic Information
    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500)
    
    # Event Schedule
    start_date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField()
    door_open_time = models.TimeField(null=True, blank=True)
    
    # Venue Information
    venue_name = models.CharField(max_length=255)
    venue_type = models.CharField(
        max_length=20, 
        choices=VenueType.choices, 
        default=VenueType.INDOOR
    )
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Virtual Event Link (if applicable)
    virtual_meeting_url = models.URLField(max_length=500, blank=True)
    virtual_meeting_password = models.CharField(max_length=100, blank=True)
    
    # Media
    banner_image = models.ImageField(upload_to='events/banners/', null=True, blank=True)
    thumbnail_image = models.ImageField(upload_to='events/thumbnails/', null=True, blank=True)
    gallery_images = models.JSONField(default=list, blank=True)  # Store array of image URLs
    
    # Status and Settings
    status = models.CharField(
        max_length=20, 
        choices=EventStatus.choices, 
        default=EventStatus.DRAFT,
        db_index=True
    )
    is_featured = models.BooleanField(default=False, db_index=True)
    is_private = models.BooleanField(default=False, help_text="Private events require invitation code")
    invitation_code = models.CharField(max_length=50, blank=True)
    
    # Capacity and Limits
    max_capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    min_age_requirement = models.PositiveIntegerField(default=0)
    
    # Organizer Information
    organizer = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        related_name='organized_events'
    )
    co_organizers = models.ManyToManyField(
        User, 
        related_name='co_organized_events',
        blank=True
    )
    
    # Metadata
    tags = models.JSONField(default=list, blank=True)
    terms_and_conditions = models.TextField(blank=True)
    refund_policy = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['start_date', 'status']),
            models.Index(fields=['city', 'start_date']),
            models.Index(fields=['organizer', '-created_at']),
        ]
        ordering = ['-start_date']
        
    def __str__(self):
        return f"{self.title} - {self.start_date.strftime('%Y-%m-%d')}"
    
    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError('End date must be after start date')
            
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
    @property
    def is_sold_out(self):
        Ticket = apps.get_model('tickets', 'Ticket')
        total_sold = Ticket.objects.filter(
            ticket_type__event=self,
            status__in=[Ticket.TicketStatus.VALID, Ticket.TicketStatus.USED]
        ).count()
        return total_sold >= self.max_capacity
    
    @property
    def available_tickets(self):
        return self.max_capacity - self.total_tickets_sold
    
    @property
    def total_tickets_sold(self):
        Ticket = apps.get_model('tickets', 'Ticket')
        return Ticket.objects.filter(
            ticket_type__event=self,
            status__in=[Ticket.TicketStatus.VALID, Ticket.TicketStatus.USED]
        ).count()
