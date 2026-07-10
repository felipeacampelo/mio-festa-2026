from rest_framework import generics, permissions

from .models import EventSettings
from .serializers import EventSettingsSerializer


class PublicEventView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EventSettingsSerializer

    def get_object(self):
        return EventSettings.get_solo()


class AdminEventView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = EventSettingsSerializer

    def get_object(self):
        return EventSettings.get_solo()
