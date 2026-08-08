import uuid

from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, response, status
from rest_framework.decorators import api_view, permission_classes

from apps.notifications.services import safe_send_order_paid_emails, safe_send_ticket_reissued_email
from apps.orders.models import Order
from apps.tickets.models import Ticket, TicketAuditLog
from apps.tickets.serializers import AdminTicketSerializer, AdminTicketTransferSerializer, AdminTicketUpdateSerializer
from apps.tickets.services import append_audit, reissue_ticket, undo_check_in


def _ticket_not_editable_response(ticket):
    if ticket.order.status != Order.Status.PAID or ticket.status == Ticket.Status.PENDING:
        return response.Response(
            {"detail": "Este pedido ainda nao possui ingresso emitido."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def paginate_queryset(request, queryset, serializer_class):
    try:
        page = max(int(request.query_params.get("page", "1")), 1)
    except ValueError:
        page = 1
    try:
        page_size = int(request.query_params.get("page_size", "50"))
    except ValueError:
        page_size = 50
    page_size = min(max(page_size, 1), 100)
    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    serializer = serializer_class(queryset[start:end], many=True)
    return response.Response(
        {
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        }
    )


class AdminOrderListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get("search", "").strip()
        orders = Order.objects.prefetch_related("tickets").select_related("payment")
        if query:
            filters = (
                Q(buyer_name__icontains=query)
                | Q(buyer_email__icontains=query)
                | Q(order_code__icontains=query)
                | Q(tickets__participant_name__icontains=query)
                | Q(tickets__participant_email__icontains=query)
            )
            try:
                filters |= Q(public_id=uuid.UUID(query))
            except ValueError:
                pass
            orders = orders.filter(filters).distinct()
        from apps.orders.serializers import OrderSerializer

        return paginate_queryset(request, orders, OrderSerializer)


class AdminTicketListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminTicketSerializer

    def get_queryset(self):
        query = self.request.query_params.get("search", "").strip()
        queryset = (
            Ticket.objects.select_related("order", "checked_in_by", "superseded_by_ticket")
            .prefetch_related("audit_logs")
            .filter(status__in=[Ticket.Status.ACTIVE, Ticket.Status.USED])
        )
        if query:
            filters = (
                Q(participant_name__icontains=query)
                | Q(participant_email__icontains=query)
                | Q(order__buyer_email__icontains=query)
                | Q(order__order_code__icontains=query)
            )
            try:
                filters |= Q(ticket_code=uuid.UUID(query))
            except ValueError:
                pass
            queryset = queryset.filter(filters)
        return queryset

    def list(self, request, *args, **kwargs):
        return paginate_queryset(request, self.get_queryset(), self.serializer_class)


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def admin_stats(request):
    total_orders = Order.objects.count()
    paid_orders_qs = Order.objects.filter(status=Order.Status.PAID)
    paid_orders = paid_orders_qs.count()
    revenue = paid_orders_qs.aggregate(total=Sum("total_amount"))["total"] or 0

    tickets_qs = Ticket.objects.filter(status__in=[Ticket.Status.ACTIVE, Ticket.Status.USED])
    total_tickets = tickets_qs.count()
    active_tickets = tickets_qs.filter(status=Ticket.Status.ACTIVE).count()
    used_tickets = tickets_qs.filter(status=Ticket.Status.USED).count()

    return response.Response(
        {
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "revenue": revenue,
            "total_tickets": total_tickets,
            "active_tickets": active_tickets,
            "used_tickets": used_tickets,
        }
    )


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def resend_order_tickets(request, order_id: int):
    order = get_object_or_404(Order.objects.prefetch_related("tickets"), pk=order_id)
    if order.status != Order.Status.PAID:
        return response.Response(
            {"detail": "Ingressos so podem ser reenviados apos pagamento confirmado."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    safe_send_order_paid_emails(order)
    for ticket in order.tickets.all():
        append_audit(ticket, TicketAuditLog.Action.RESENT, note="Ingressos reenviados manualmente.", actor=request.user)
    return response.Response({"ok": True})


@api_view(["PATCH"])
@permission_classes([permissions.IsAdminUser])
def edit_ticket(request, ticket_id: int):
    ticket = get_object_or_404(Ticket.objects.select_related("order"), pk=ticket_id)
    not_editable = _ticket_not_editable_response(ticket)
    if not_editable is not None:
        return not_editable
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
    safe_send_ticket_reissued_email(replacement, ticket.order.buyer_email)
    return response.Response(AdminTicketSerializer(replacement).data)


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def transfer_ticket(request, ticket_id: int):
    ticket = get_object_or_404(Ticket.objects.select_related("order"), pk=ticket_id)
    not_editable = _ticket_not_editable_response(ticket)
    if not_editable is not None:
        return not_editable
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
    safe_send_ticket_reissued_email(replacement, ticket.order.buyer_email)
    return response.Response(AdminTicketSerializer(replacement).data)


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def admin_undo_check_in(request, ticket_id: int):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    result = undo_check_in(ticket, actor=request.user)
    if result == "not_checked_in":
        return response.Response(
            {"detail": "Este ingresso nao esta com check-in feito."}, status=status.HTTP_400_BAD_REQUEST
        )
    return response.Response(AdminTicketSerializer(ticket).data)
