from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import permissions, response
from rest_framework.decorators import api_view, permission_classes

from apps.tickets.admin_views import paginate_queryset

from . import services
from .models import Card, CardTransaction
from .serializers import AdminCardListSerializer


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def admin_card_list(request):
    query = request.query_params.get("search", "").strip()
    cards = Card.objects.select_related("ticket").order_by("-created_at")
    if query:
        digits = "".join(ch for ch in query if ch.isdigit())
        filters = Q(uid__icontains=query) | Q(ticket__participant_name__icontains=query)
        if digits:
            filters |= Q(ticket__participant_document__icontains=digits)
        cards = cards.filter(filters)
    return paginate_queryset(request, cards, AdminCardListSerializer)


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def admin_card_reconciliation(request):
    by_vendor = list(
        CardTransaction.objects.filter(type=CardTransaction.Type.CREDIT)
        .values("vendor_id", "vendor__display_name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    outstanding = (
        Card.objects.filter(status__in=[Card.Status.ACTIVE, Card.Status.BLOCKED]).aggregate(total=Sum("balance"))[
            "total"
        ]
        or 0
    )
    status_counts = {
        choice_value: Card.objects.filter(status=choice_value).count() for choice_value, _ in Card.Status.choices
    }
    return response.Response(
        {
            "recharge_by_vendor": by_vendor,
            "outstanding_balance": outstanding,
            "status_counts": status_counts,
        }
    )


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def admin_block_card(request, uid):
    card = get_object_or_404(Card, uid=services.normalize_uid(uid))
    services.block_card(card, note=request.data.get("note", ""))
    return response.Response(AdminCardListSerializer(card).data)


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def admin_unblock_card(request, uid):
    card = get_object_or_404(Card, uid=services.normalize_uid(uid))
    services.unblock_card(card, note=request.data.get("note", ""))
    return response.Response(AdminCardListSerializer(card).data)


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def admin_return_card(request, uid):
    card = get_object_or_404(Card, uid=services.normalize_uid(uid))
    services.return_card(card, note=request.data.get("note", ""))
    return response.Response(AdminCardListSerializer(card).data)
