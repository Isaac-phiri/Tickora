from .models import Payment
from orders.models import Order, OrderItem
from tickets.models import Ticket
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

@receiver(post_save, sender=OrderItem)
def update_order_totals(sender, instance, created, **kwargs):
    """Update order totals when order items change"""
    instance.order.calculate_totals()

@receiver(post_save, sender=Payment)
def update_order_payment_status(sender, instance, **kwargs):
    """Update order status based on payment"""
    if instance.status == Payment.PaymentStatus.COMPLETED:
        instance.order.status = Order.OrderStatus.PAID
        instance.order.payment_date = instance.payment_date
        instance.order.save()
    elif instance.status == Payment.PaymentStatus.FAILED:
        instance.order.status = Order.OrderStatus.FAILED
        instance.order.save()

@receiver(post_save, sender=Order)
def create_tickets_after_payment(sender, instance, created, **kwargs):
    """Generate individual tickets after order is paid"""
    if instance.status == Order.OrderStatus.PAID:
        # Check if tickets already exist for this order
        if not instance.tickets.exists():
            for order_item in instance.order_items.all():
                for _ in range(order_item.quantity):
                    Ticket.objects.create(
                        order=instance,
                        order_item=order_item,
                        ticket_type=order_item.ticket_type,
                        event=instance.event,
                        attendee_email=instance.email
                    )