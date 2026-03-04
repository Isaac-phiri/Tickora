from decimal import Decimal
from django.conf import settings
from tickets.models import TicketType


class Cart:
    """
    Shopping cart class for managing ticket purchases
    """
    
    def __init__(self, request):
        """
        Initialize the cart
        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        
        if not cart:
            # Save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        
        self.cart = cart
    
    def add(self, ticket_type, quantity=1, update_quantity=False):
        """
        Add a ticket to the cart or update its quantity
        """
        ticket_type_id = str(ticket_type.id)
        
        if ticket_type_id not in self.cart:
            self.cart[ticket_type_id] = {
                'quantity': 0,
                'price': str(ticket_type.current_price),
                'name': ticket_type.name,
                'event_id': ticket_type.event_id,
                'event_title': ticket_type.event.title,
                'max_per_order': ticket_type.max_per_order,
                'ticket_type_id': ticket_type_id
            }
        
        if update_quantity:
            self.cart[ticket_type_id]['quantity'] = quantity
        else:
            self.cart[ticket_type_id]['quantity'] += quantity
        
        self.save()
    
    def save(self):
        """
        Mark the session as modified to ensure it gets saved
        """
        self.session.modified = True
    
    def remove(self, ticket_type):
        """
        Remove a ticket from the cart
        """
        ticket_type_id = str(ticket_type.id)
        
        if ticket_type_id in self.cart:
            del self.cart[ticket_type_id]
            self.save()
    
    def __iter__(self):
        """
        Iterate over the items in the cart and get the tickets from the database
        """
        ticket_type_ids = self.cart.keys()
        ticket_types = TicketType.objects.filter(id__in=ticket_type_ids)
        
        cart = self.cart.copy()
        
        for ticket_type in ticket_types:
            cart[str(ticket_type.id)]['ticket_type'] = ticket_type
        
        for item in cart.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item
    
    def __len__(self):
        """
        Count all items in the cart
        """
        return sum(item['quantity'] for item in self.cart.values())
    
    def get_total_price(self):
        """
        Calculate total cost of items in cart
        """
        return sum(
            Decimal(item['price']) * item['quantity']
            for item in self.cart.values()
        )
    
    def get_total_quantity(self):
        """
        Get total quantity of tickets
        """
        return sum(item['quantity'] for item in self.cart.values())
    
    def clear(self):
        """
        Remove cart from session
        """
        del self.session[settings.CART_SESSION_ID]
        self.save()
    
    def get_event_ids(self):
        """
        Get unique event IDs in cart
        """
        events = set()
        for item in self.cart.values():
            events.add(item['event_id'])
        return events
    
    def validate_availability(self):
        """
        Check if all items in cart are still available
        Returns (is_valid, errors)
        """
        errors = []
        is_valid = True
        
        for item in self:
            ticket_type = item['ticket_type']
            
            # Check if ticket type exists and is still available
            if not ticket_type:
                errors.append(f"{item['name']} is no longer available.")
                is_valid = False
                continue
            
            # Check if within sales period
            from django.utils import timezone
            now = timezone.now()
            if now < ticket_type.sales_start_date or now > ticket_type.sales_end_date:
                errors.append(f"{ticket_type.name} is not available for purchase at this time.")
                is_valid = False
                continue
            
            # Check available quantity
            if item['quantity'] > ticket_type.tickets_remaining:
                errors.append(
                    f"Only {ticket_type.tickets_remaining} tickets available for {ticket_type.name}."
                )
                is_valid = False
                continue
            
            # Check per-order limits
            if item['quantity'] > ticket_type.max_per_order:
                errors.append(
                    f"Maximum {ticket_type.max_per_order} tickets allowed per order for {ticket_type.name}."
                )
                is_valid = False
                continue
            
            # Check if event is still available
            if ticket_type.event.is_sold_out or ticket_type.event.status != 'published':
                errors.append(f"{ticket_type.event.title} is no longer available.")
                is_valid = False
                continue
            
            # Check if event hasn't started
            if ticket_type.event.start_date < now:
                errors.append(f"{ticket_type.event.title} has already started or passed.")
                is_valid = False
                continue
        
        return is_valid, errors