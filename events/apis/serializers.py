from rest_framework import serializers
from events.models import Event

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            'id', 'organizer', 'image', 'event_type', 'event_name', 'description', 
            'price', 'date_and_time', 'venue', 'total_tickets', 'tickets_sold', 
            'max_attendees', 'is_public', 'status', 'timestamp', 'updated_at'
        ]
