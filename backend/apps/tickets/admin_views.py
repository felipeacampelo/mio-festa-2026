import uuid

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, response, status
from rest_framework.decorators import api_view, permission_classes

from apps.notifications.services import send_order_paid_emails, send_ticket_reissued_email
from apps.orders.models import Order
from apps.tickets.models import Ticket, TicketAuditLog
from apps.tickets.serializers import AdminTicketSerializer, AdminTicketTransferSerializer, AdminTicketUpdateSerializer
from apps.tickets.services import append_audit, reissue_ticket


class AdminOrderListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get("search", "").strip()
        orders = Order.objects.prefetch_related("tickets").select_related("payment")
        if query:
            filters = (
                Q(buyer_name__icontains=query)
                | Q(buyer_email__icontains=query)
                | Q(tickets__participant_name__icontains=query)
                | Q(tickets__participant_email__icontains=query)
            )
            try:
                filters |= Q(public_id=uuid.UUID(query))
            except ValueError:
                pass
            orders = orders.filter(filters).distinct()
        from apps.orders.serializers import OrderSerializer

        return response.Response(OrderSerializer(orders, many=True).data)


class AdminTicketListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminTicketSerializer

    def get_queryset(self):
        query = self.request.query_params.get("search", "").strip()
        queryset = Ticket.objects.select_related("order", "checked_in_by", "superseded_by_ticket").prefetch_related("audit_logs")
        if query:
            filters = (
                Q(participant_name__icontains=query)
                | Q(participant_email__icontains=query)
                | Q(order__buyer_email__icontains=query)
            )
            try:
                filters |= Q(ticket_code=uuid.UUID(query))
            except ValueError:
                pass
            queryset = queryset.filter(filters)
        return queryset


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def resend_order_tickets(request, order_id: int):
    order = get_object_or_404(Order.objects.prefetch_related("tickets"), pk=order_id)
    send_order_paid_emails(order)
    for ticket in order.tickets.all():
        append_audit(ticket, TicketAuditLog.Action.RESENT, note="Ingressos reenviados manualmente.", actor=request.user)
    return response.Response({"ok": True})


@api_view(["PATCH"])
@permission_classes([permissions.IsAdminUser])
def edit_ticket(request, ticket_id: int):
    ticket = get_object_or_404(Ticket.objects.select_related("order"), pk=ticket_id)
    if ticket.status == Ticket.Status.USED:
        return response.Response({"detail": "Nao e possivel editar ticket ja utilizado."}, status=status.HTTP_400_BAD_REQUEST)
    serializer = AdminTicketUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    replacement = reissue_ticket(
        ticket,
        participant_name=serializer.validated_data["participant_name"],
        participant_email=serializer.validated_data.get("participant_email", ""),
        actor=request.user,
        action=TicketAuditLog.Action.EDITED,
    )
    send_ticket_reissued_email(replacement, ticket.order.buyer_email)
    return response.Response(AdminTicketSerializer(replacement).data)


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def transfer_ticket(request, ticket_id: int):
    ticket = get_object_or_404(Ticket.objects.select_related("order"), pk=ticket_id)
    if ticket.status == Ticket.Status.USED:
        return response.Response({"detail": "Nao e possivel transferir ticket ja utilizado."}, status=status.HTTP_400_BAD_REQUEST)
    serializer = AdminTicketTransferSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    replacement = reissue_ticket(
        ticket,
        participant_name=serializer.validated_data["participant_name"],
        participant_email=serializer.validated_data.get("participant_email", ""),
        actor=request.user,
        action=TicketAuditLog.Action.TRANSFERRED,
    )
    send_ticket_reissued_email(replacement, ticket.order.buyer_email)
    return response.Response(AdminTicketSerializer(replacement).data)
