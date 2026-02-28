from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from events.models import Event
from .serializers import EventSerializer



class EventViewSet(ViewSet):
    
    serializers = EventSerializer
    model = Event

    def get_object(self, pk):
        try:
            return self.model.objects.get(pk=pk)
        except self.model.DoesNotExist:
            return Response(status=404)

    def list(self, request):
        events = self.model.objects.all()
        serializer = self.serializers(events, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        event = Event.objects.get(pk=pk)
        serializer = self.serializers(event)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.serializers(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def update(self, request, pk=None):
        event = Event.objects.get(pk=pk)
        serializer = self.serializers(event, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def destroy(self, request, pk=None):
        
        try:
            event = Event.objects.get(pk=pk)
        except self.model.DoesNotExist:
            return Response(status=404)
        
        event.delete()
        event = Event.objects.all()
        serializer = self.serializers(event, many=True)
        return Response(serializer.data)
