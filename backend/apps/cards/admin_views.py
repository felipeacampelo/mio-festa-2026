from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import permissions, response
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes

from apps.tickets.admin_views import paginate_queryset

from . import services
from .models import Card, CardTransaction, CardTransactionItem, Product, Vendor
from .serializers import AdminCardListSerializer, ProductSerializer, VendorOptionSerializer, VendorSerializer


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
    if request.query_params.get("exclude_returned") == "true":
        cards = cards.exclude(status=Card.Status.RETURNED)
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
    # Agrupa por product_name (snapshot) + vendedor do produto, nao so pela
    # FK de Product - assim continua contando itens vendidos mesmo se o
    # produto foi excluido depois (vendor fica nulo nesse caso), e o preco
    # usado e o congelado no momento da venda de cada item, nao o preco
    # atual do produto.
    sold_by_product = list(
        CardTransactionItem.objects.values("product_name", "product__vendor_id", "product__vendor__display_name")
        # Duas chamadas .annotate() separadas de proposito: anotar "quantity"
        # e "total" (que usa F("quantity")) na MESMA chamada faz o Django
        # resolver o F() contra o alias "quantity" ja anotado (um Sum), nao
        # contra o campo original - e agregado dentro de agregado quebra.
        .annotate(
            total=Sum(
                ExpressionWrapper(F("quantity") * F("unit_price"), output_field=DecimalField(max_digits=12, decimal_places=2))
            )
        )
        .annotate(quantity=Sum("quantity"))
        .order_by("product__vendor__display_name", "-quantity")
    )
    sold_by_product = [
        {
            "product_name": row["product_name"],
            "vendor_id": row["product__vendor_id"],
            "vendor_name": row["product__vendor__display_name"],
            "quantity": row["quantity"],
            "total": row["total"],
        }
        for row in sold_by_product
    ]
    return response.Response(
        {
            "recharge_by_vendor": by_vendor,
            "sold_by_vendor": sold_by_vendor,
            "sold_by_product": sold_by_product,
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


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def admin_vendor_list(request):
    vendors = Vendor.objects.order_by("role", "display_name")
    return response.Response(VendorSerializer(vendors, many=True).data)


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def admin_vendor_impersonate(request, pk):
    # Permite o admin entrar direto num vendedor/caixa/checkin ja cadastrado
    # sem saber a senha - util pra suporte durante o evento (celular travou,
    # esqueceu a senha etc). Reaproveita a conta real (e o catalogo real, no
    # caso de vendedor) em vez de criar uma conta fantasma so pro admin.
    vendor = get_object_or_404(Vendor, pk=pk)
    if not vendor.is_active:
        return response.Response({"detail": "Vendedor inativo."}, status=400)
    token, _ = Token.objects.get_or_create(user=vendor.user)
    return response.Response(
        {
            "token": token.key,
            "vendor": {"id": vendor.id, "display_name": vendor.display_name, "role": vendor.role},
        }
    )


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
