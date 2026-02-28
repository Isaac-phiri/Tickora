from django.db import models
from orders.models import Order

class Transaction(models.Model):
    
    TRANSACTION_STATUS = (
        ('Success', 'Success'),
        ('Failure', 'Failure')
    )
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=100)
    transaction_date_and_time = models.DateTimeField()
    transaction_status = models.CharField(max_length=20)  # Success, Failure
    transaction_amount = models.DecimalField(max_digits=10, decimal_places=2)  
    transaction_id = models.CharField(max_length=100, null=True, blank=True)  
    payment_gateway_response = models.TextField(null=True, blank=True)  #

    def __str__(self):
        return str(self.transaction_id)