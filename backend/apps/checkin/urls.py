from django.urls import path

from .views import manual_checkin, scan_checkin


urlpatterns = [
    path("scan/", scan_checkin, name="checkin-scan"),
    path("manual/", manual_checkin, name="checkin-manual"),
]
