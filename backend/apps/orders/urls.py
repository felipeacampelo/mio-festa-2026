from django.urls import path

from .views import OrderCreateView, OrderDetailView, OrderLookupView


urlpatterns = [
    path("checkout/", OrderCreateView.as_view(), name="order-checkout"),
    path("lookup/", OrderLookupView.as_view(), name="order-lookup"),
    path("<uuid:public_id>/", OrderDetailView.as_view(), name="order-detail"),
]
