from django.urls import path

from .admin_views import (
    AdminOrderListView,
    AdminTicketListView,
    admin_stats,
    admin_undo_check_in,
    edit_ticket,
    resend_order_tickets,
    transfer_ticket,
)


urlpatterns = [
    path("stats/", admin_stats, name="admin-stats"),
    path("orders/", AdminOrderListView.as_view(), name="admin-order-list"),
    path("orders/<int:order_id>/resend-tickets/", resend_order_tickets, name="admin-order-resend"),
    path("tickets/", AdminTicketListView.as_view(), name="admin-ticket-list"),
    path("tickets/<int:ticket_id>/", edit_ticket, name="admin-ticket-edit"),
    path("tickets/<int:ticket_id>/transfer/", transfer_ticket, name="admin-ticket-transfer"),
    path("tickets/<int:ticket_id>/undo-checkin/", admin_undo_check_in, name="admin-ticket-undo-checkin"),
]
