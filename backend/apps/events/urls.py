from django.urls import path

from .views import AdminEventView, PublicEventView


urlpatterns = [
    path("current/", PublicEventView.as_view(), name="event-current"),
    path("admin/current/", AdminEventView.as_view(), name="event-admin-current"),
]
