# models.py
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
from orders.models import Order

 
class Payment(BaseModel):
    """
    Payment transaction model linked to orders
    """
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
        PARTIALLY_REFUNDED = 'partially_refunded', 'Partially Refunded'
        CHARGEBACK = 'chargeback', 'Chargeback'

    class PaymentGateway(models.TextChoices):
        STRIPE = 'stripe', 'Stripe'
        PAYPAL = 'paypal', 'PayPal'
        BRAINTREE = 'braintree', 'Braintree'
        AUTHORIZE_NET = 'authorize_net', 'Authorize.net'
        SQUARE = 'square', 'Square'

    # Relationships
    order = models.OneToOneField(
        'orders.Order', 
        on_delete=models.PROTECT,
        related_name='payment',
        primary_key=True
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True,
        related_name='payments'
    )
    
    # Payment Details
    transaction_id = models.CharField(
        max_length=255, 
        unique=True, 
        db_index=True
    )
    gateway = models.CharField(
        max_length=20, 
        choices=PaymentGateway.choices
    )
    status = models.CharField(
        max_length=20, 
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True
    )
    
    # Financials
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='USD')
    gateway_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    net_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        editable=False
    )
    
    # Payment Method Details
    payment_method = models.CharField(
        max_length=50, 
        choices=Order.PaymentMethod.choices
    )
    last_four = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=50, blank=True)
    
    # Gateway Response Data
    gateway_response = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    
    # Refund Information
    refunded_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    refund_transaction_id = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    payment_date = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['gateway', 'status']),
            models.Index(fields=['user', '-payment_date']),
        ]
        ordering = ['-payment_date']
        
    def __str__(self):
        return f"Payment {self.transaction_id} - {self.amount} {self.currency}"
    
    def save(self, *args, **kwargs):
        self.net_amount = self.amount - self.gateway_fee
        super().save(*args, **kwargs)
    
    def process_refund(self, amount=None, transaction_id=None):
        """Process a refund for this payment"""
        refund_amount = amount if amount else self.amount
        
        if refund_amount > (self.amount - self.refunded_amount):
            raise ValidationError("Refund amount exceeds available balance")
        
        self.refunded_amount += refund_amount
        if self.refunded_amount >= self.amount:
            self.status = self.PaymentStatus.REFUNDED
        else:
            self.status = self.PaymentStatus.PARTIALLY_REFUNDED
        
        if transaction_id:
            self.refund_transaction_id = transaction_id
        
        self.save()

