from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import permissions, response
from rest_framework.decorators import api_view, permission_classes

from apps.tickets.admin_views import paginate_queryset

from . import services
from .models import Card, CardTransaction, CardTransactionItem, Product, Vendor
from .serializers import AdminCardListSerializer, ProductSerializer, VendorOptionSerializer


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
    sold_by_vendor = list(
        CardTransaction.objects.filter(type=CardTransaction.Type.DEBIT)
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
            "sold_by_vendor": sold_by_vendor,
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


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def admin_seller_list(request):
    sellers = Vendor.objects.filter(role=Vendor.Role.SELLER).order_by("display_name")
    return response.Response(VendorOptionSerializer(sellers, many=True).data)


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAdminUser])
def admin_product_list(request):
    if request.method == "POST":
        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(serializer.data, status=201)

    query = request.query_params.get("search", "").strip()
    products = Product.objects.select_related("vendor").order_by("vendor__display_name", "name")
    if query:
        products = products.filter(Q(name__icontains=query) | Q(vendor__display_name__icontains=query))
    vendor_id = request.query_params.get("vendor", "").strip()
    if vendor_id:
        products = products.filter(vendor_id=vendor_id)
    return paginate_queryset(request, products, ProductSerializer)


@api_view(["PATCH", "DELETE"])
@permission_classes([permissions.IsAdminUser])
def admin_product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "DELETE":
        if CardTransactionItem.objects.filter(product=product).exists():
            return response.Response(
                {"detail": "Produto ja foi usado em vendas. Desative em vez de excluir."},
                status=400,
            )
        product.delete()
        return response.Response(status=204)

    serializer = ProductSerializer(product, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return response.Response(serializer.data)
