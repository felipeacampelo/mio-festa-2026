from decimal import Decimal

from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import permissions, response, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import AuthenticationFailed

from apps.core.throttling import LoginRateThrottle
from apps.tickets.models import Ticket

from . import services
from .models import CardTransaction, Product
from .permissions import IsCheckin, IsRecharge, IsSeller, IsVendor
from .serializers import (
    CardAmountSerializer,
    CardCartSerializer,
    CardLinkSerializer,
    CardSerializer,
    CardTransactionItemSerializer,
    ProductSerializer,
    TicketSearchResultSerializer,
    VendorLoginSerializer,
)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([LoginRateThrottle])
def vendor_login(request):
    serializer = VendorLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = authenticate(
        username=serializer.validated_data["username"],
        password=serializer.validated_data["password"],
    )
    vendor = getattr(user, "vendor_profile", None) if user else None
    if not user or not vendor or not vendor.is_active:
        raise AuthenticationFailed("Credenciais invalidas.")
    token, _ = Token.objects.get_or_create(user=user)
    return response.Response(
        {
            "token": token.key,
            "vendor": {"id": vendor.id, "display_name": vendor.display_name, "role": vendor.role},
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsVendor])
def vendor_me(request):
    vendor = request.user.vendor_profile
    return response.Response({"id": vendor.id, "display_name": vendor.display_name, "role": vendor.role})


@api_view(["GET"])
@permission_classes([IsVendor])
def get_card(request, uid):
    card = services.get_or_create_card(uid)
    return response.Response(CardSerializer(card).data)


@api_view(["GET"])
@permission_classes([IsCheckin])
def search_tickets(request):
    query = request.query_params.get("q", "").strip()
    if not query:
        return response.Response([])
    digits = "".join(ch for ch in query if ch.isdigit())
    filters = Q(participant_name__icontains=query)
    if digits:
        filters |= Q(participant_document__icontains=digits)
    tickets = (
        Ticket.objects.select_related("order")
        .filter(status__in=[Ticket.Status.ACTIVE, Ticket.Status.USED])
        .filter(filters)[:20]
    )
    return response.Response(TicketSearchResultSerializer(tickets, many=True).data)


@api_view(["POST"])
@permission_classes([IsCheckin])
def link_card(request, uid):
    serializer = CardLinkSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    result, card = services.link_card(uid, serializer.validated_data["ticket_id"])
    payload = {"result": result}
    if card is not None:
        payload["card"] = CardSerializer(card).data
    return response.Response(payload)


@api_view(["GET"])
@permission_classes([IsSeller])
def list_products(request):
    products = Product.objects.filter(is_active=True, vendor=request.user.vendor_profile)
    return response.Response(ProductSerializer(products, many=True).data)


@api_view(["POST"])
@permission_classes([IsSeller])
def debit_card(request, uid):
    vendor = request.user.vendor_profile
    if "items" in request.data:
        serializer = CardCartSerializer(data=request.data, context={"vendor": vendor})
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["items"]
        amount = sum((product.price * qty for product, qty in items), Decimal("0.00"))
        idempotency_key = serializer.validated_data["idempotency_key"]
        result, card = services.debit_card(
            uid,
            amount,
            vendor,
            idempotency_key,
            serializer.validated_data.get("note", ""),
            items=items,
        )
    else:
        serializer = CardAmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = serializer.validated_data["idempotency_key"]
        result, card = services.debit_card(
            uid,
            serializer.validated_data["amount"],
            vendor,
            idempotency_key,
            serializer.validated_data.get("note", ""),
        )
    payload = {"result": result}
    if card is not None:
        payload["card"] = CardSerializer(card).data
        if result == "ok":
            txn = CardTransaction.objects.filter(idempotency_key=idempotency_key).first()
            if txn is not None and txn.items.exists():
                payload["items"] = CardTransactionItemSerializer(txn.items.all(), many=True).data
    return response.Response(payload)


@api_view(["POST"])
@permission_classes([IsRecharge])
def credit_card(request, uid):
    serializer = CardAmountSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    result, card = services.credit_card(
        uid,
        serializer.validated_data["amount"],
        request.user.vendor_profile,
        serializer.validated_data["idempotency_key"],
        serializer.validated_data.get("note", ""),
    )
    payload = {"result": result}
    if card is not None:
        payload["card"] = CardSerializer(card).data
    return response.Response(payload)
