from django.db import models
from accounts.models import User
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
from orders.models import Order, OrderItem
from events.models import Event


class TicketType(BaseModel):
    """
    Ticket categories/types for an event (e.g., VIP, Early Bird, General Admission)
    """
    class TicketClass(models.TextChoices):
        VIP = 'vip', 'VIP'
        EARLY_BIRD = 'early_bird', 'Early Bird'
        GENERAL = 'general', 'General Admission'
        STUDENT = 'student', 'Student'
        SENIOR = 'senior', 'Senior'
        GROUP = 'group', 'Group'
        COMPLIMENTARY = 'complimentary', 'Complimentary'

    event = models.ForeignKey(
        'events.Event', 
        on_delete=models.CASCADE,
        related_name='ticket_types'
    )
    name = models.CharField(max_length=255)
    ticket_class = models.CharField(
        max_length=20, 
        choices=TicketClass.choices,
        default=TicketClass.GENERAL
    )
    description = models.TextField(blank=True)
    
    # Pricing
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    early_bird_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True
    )
    early_bird_end_date = models.DateTimeField(null=True, blank=True)
    
    # Inventory
    quantity_available = models.PositiveIntegerField(
        validators=[MinValueValidator(0)]
    )
    max_per_order = models.PositiveIntegerField(default=10)
    min_per_order = models.PositiveIntegerField(default=1)
    
    # Sales Period
    sales_start_date = models.DateTimeField(db_index=True)
    sales_end_date = models.DateTimeField(db_index=True)
    
    # Fees
    service_fee_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    service_fee_fixed = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['event', 'ticket_class']),
            models.Index(fields=['event', 'sales_start_date', 'sales_end_date']),
        ]
        ordering = ['price', 'name']
        
    def __str__(self):
        return f"{self.event.title} - {self.name}"
    
    @property
    def current_price(self):
        """Returns early bird price if applicable, otherwise regular price"""
        if (self.early_bird_price and 
            self.early_bird_end_date and 
            timezone.now() <= self.early_bird_end_date):
            return self.early_bird_price
        return self.price
    
    @property
    def tickets_sold(self):
        return self.tickets.filter(
            status__in=[Ticket.TicketStatus.VALID, Ticket.TicketStatus.USED]
        ).count()
    
    @property
    def tickets_remaining(self):
        return self.quantity_available - self.tickets_sold
    
    @property
    def is_sold_out(self):
        return self.tickets_remaining <= 0
    
    def clean(self):
        if self.sales_end_date <= self.sales_start_date:
            raise ValidationError('Sales end date must be after sales start date')
        if self.early_bird_end_date and self.early_bird_end_date > self.sales_end_date:
            raise ValidationError('Early bird end date must be before sales end date')




class Ticket(BaseModel):
    """
    Individual ticket instance with unique identifier for entry
    """
    class TicketStatus(models.TextChoices):
        VALID = 'valid', 'Valid'
        USED = 'used', 'Used'
        REFUNDED = 'refunded', 'Refunded'
        CANCELLED = 'cancelled', 'Cancelled'
        EXPIRED = 'expired', 'Expired'

    # Unique ticket identifier
    ticket_number = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        default=uuid.uuid4().hex.upper()
    )
    
    # Relationships
    order = models.ForeignKey(
        'orders.Order', 
        on_delete=models.PROTECT,
        related_name='tickets'
    )
    order_item = models.ForeignKey(
        'orders.OrderItem', 
        on_delete=models.PROTECT,
        related_name='tickets'
    )
    ticket_type = models.ForeignKey(
        'tickets.TicketType', 
        on_delete=models.PROTECT,
        related_name='tickets'
    )
    event = models.ForeignKey(
        'events.Event', 
        on_delete=models.PROTECT,
        related_name='tickets'
    )
    
    # Ticket Details
    status = models.CharField(
        max_length=20, 
        choices=TicketStatus.choices, 
        default=TicketStatus.VALID,
        db_index=True
    )
    
    # Attendee Information (for assigned tickets)
    attendee_name = models.CharField(max_length=255, blank=True)
    attendee_email = models.EmailField(blank=True)
    attendee_phone = models.CharField(max_length=20, blank=True)
    
    # Security
    qr_code = models.ImageField(upload_to='tickets/qrcodes/', blank=True)
    qr_secret = models.CharField(max_length=255, unique=True, default=uuid.uuid4)
    check_in_code = models.CharField(max_length=10, blank=True)
    
    # Check-in tracking
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checked_in_tickets'
    )
    check_in_ip = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['ticket_number']),
            models.Index(fields=['qr_secret']),
            models.Index(fields=['event', 'status']),
            models.Index(fields=['order', 'status']),
            models.Index(fields=['attendee_email']),
        ]
        ordering = ['created_at']
        
    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.event.title}"
    
    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.generate_qr_code()
        if not self.check_in_code:
            self.check_in_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)
    
    def generate_qr_code(self):
        """Generate QR code for the ticket"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        # QR data contains ticket verification info
        qr_data = f"TICKET:{self.ticket_number}:{self.qr_secret}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        self.qr_code.save(
            f'ticket_{self.ticket_number}.png',
            ContentFile(buffer.getvalue()),
            save=False
        )
    
    def check_in(self, user, ip_address=None):
        """Mark ticket as used"""
        if self.status != self.TicketStatus.VALID:
            raise ValidationError(f"Cannot check in ticket with status: {self.status}")
        
        self.status = self.TicketStatus.USED
        self.checked_in_at = timezone.now()
        self.checked_in_by = user
        self.check_in_ip = ip_address
        self.save()
        
    @property
    def is_valid_for_entry(self):
        return self.status == self.TicketStatus.VALID

