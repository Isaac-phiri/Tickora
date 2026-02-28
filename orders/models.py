# models.py
from django.db import models
from accounts.models import User, BaseModel
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.db.models import Q, Sum, F
from django.core.exceptions import ValidationError

class Order(BaseModel):
    """
    Order model representing a customer's purchase transaction
    """
    class OrderStatus(models.TextChoices):
        PENDING = 'pending', 'Pending Payment'
        PROCESSING = 'processing', 'Processing'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Payment Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'
        EXPIRED = 'expired', 'Expired'

    class PaymentMethod(models.TextChoices):
        CREDIT_CARD = 'credit_card', 'Credit Card'
        DEBIT_CARD = 'debit_card', 'Debit Card'
        PAYPAL = 'paypal', 'PayPal'
        STRIPE = 'stripe', 'Stripe'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CRYPTO = 'crypto', 'Cryptocurrency'
        GIFT_CARD = 'gift_card', 'Gift Card'

    # Unique identifier for the order
    order_number = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        default=uuid.uuid4().hex[:12].upper()
    )
    
    # Customer Information
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders'
    )
    email = models.EmailField(db_index=True)
    phone_number = models.CharField(max_length=20)
    
    # Guest checkout support
    is_guest_checkout = models.BooleanField(default=False)
    
    # Order Details
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.PROTECT,
        related_name='orders'
    )
    status = models.CharField(
        max_length=20, 
        choices=OrderStatus.choices, 
        default=OrderStatus.PENDING,
        db_index=True
    )
    
    # Financials
    subtotal = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    service_fee_total = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    discount_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Payment
    payment_method = models.CharField(
        max_length=20, 
        choices=PaymentMethod.choices,
        null=True,
        blank=True
    )
    payment_intent_id = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    order_date = models.DateTimeField(default=timezone.now, db_index=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateTimeField()  # When pending order expires
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', '-order_date']),
            models.Index(fields=['email', '-order_date']),
            models.Index(fields=['status', 'expiry_date']),
        ]
        ordering = ['-order_date']
        
    def __str__(self):
        return f"Order {self.order_number} - {self.email}"
    
    def save(self, *args, **kwargs):
        if not self.expiry_date:
            self.expiry_date = timezone.now() + timezone.timedelta(minutes=30)
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        """Calculate all order totals based on order items"""
        items = self.order_items.all()
        self.subtotal = sum(item.subtotal for item in items)
        self.service_fee_total = sum(item.service_fee for item in items)
        self.tax_amount = sum(item.tax_amount for item in items)
        self.total_amount = self.subtotal + self.service_fee_total + self.tax_amount - self.discount_amount
        self.save()
    
    @property
    def is_expired(self):
        return self.status == Order.OrderStatus.PENDING and timezone.now() > self.expiry_date
    
    @property
    def ticket_count(self):
        return self.order_items.aggregate(total=Sum('quantity'))['total'] or 0


class OrderItem(BaseModel):
    """
    Individual line items within an order
    """
    order = models.ForeignKey(
        'orders.Order', 
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    ticket_type = models.ForeignKey(
        'tickets.TicketType', 
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    
    # Item Details
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2
    )  # Price at time of purchase
    
    # Calculated fields
    subtotal = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        editable=False
    )
    service_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['order', 'ticket_type']),
        ]
        
    def __str__(self):
        return f"{self.quantity}x {self.ticket_type.name} - Order {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)
