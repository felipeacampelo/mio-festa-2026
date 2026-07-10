from django.urls import path

from .views import admin_force_confirm, admin_sync_payment, asaas_webhook


urlpatterns = [
    path("webhook/asaas/", asaas_webhook, name="payment-webhook-asaas"),
    path("admin/orders/<int:order_id>/confirm/", admin_force_confirm, name="admin-force-confirm"),
    path("admin/orders/<int:order_id>/sync/", admin_sync_payment, name="admin-sync-payment"),
]
