from django.urls import path

from .views import AdminCourtesyOrderCreateView, OrderCreateView, OrderDetailView, OrderLookupView


urlpatterns = [
    path("checkout/", OrderCreateView.as_view(), name="order-checkout"),
    path("lookup/", OrderLookupView.as_view(), name="order-lookup"),
    path("admin/courtesy/", AdminCourtesyOrderCreateView.as_view(), name="admin-courtesy-create"),
    path("<uuid:public_id>/", OrderDetailView.as_view(), name="order-detail"),
]
