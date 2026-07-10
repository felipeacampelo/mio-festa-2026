from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.users.urls")),
    path("api/events/", include("apps.events.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/checkin/", include("apps.checkin.urls")),
    path("api/admin/", include("apps.tickets.admin_urls")),
]
