from decimal import Decimal

from rest_framework import serializers

from apps.tickets.models import Ticket

from . import services
from .models import Card, CardTransaction, CardTransactionItem, Product, Vendor


class VendorLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class CardAmountSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    idempotency_key = serializers.CharField(max_length=64)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class CardLinkSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField()


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "price", "is_active", "created_at", "updated_at"]


class CartItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class CardCartSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)
    idempotency_key = serializers.CharField(max_length=64)
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Carrinho vazio.")
        ids = [i["product_id"] for i in items]
        products = {p.id: p for p in Product.objects.filter(id__in=ids, is_active=True)}
        missing = set(ids) - set(products)
        if missing:
            raise serializers.ValidationError("Produto invalido ou inativo.")
        merged: dict[int, int] = {}
        for i in items:
            merged[i["product_id"]] = merged.get(i["product_id"], 0) + i["quantity"]
        return [(products[pid], qty) for pid, qty in merged.items()]


class CardTransactionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardTransactionItem
        fields = ["product_name", "unit_price", "quantity"]


class TicketSearchResultSerializer(serializers.ModelSerializer):
    order_buyer_name = serializers.CharField(source="order.buyer_name", read_only=True)
    has_card = serializers.SerializerMethodField()
    purchased_on_event_day = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "ticket_code",
            "participant_name",
            "participant_document",
            "is_child",
            "order_buyer_name",
            "has_card",
            "purchased_on_event_day",
        ]

    def get_has_card(self, obj: Ticket) -> bool:
        return Card.objects.filter(ticket=obj).exists()

    def get_purchased_on_event_day(self, obj: Ticket) -> bool:
        return services.is_purchased_on_event_day(obj)


class CardTransactionSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.display_name", read_only=True)

    class Meta:
        model = CardTransaction
        fields = ["id", "type", "amount", "balance_after", "vendor_name", "note", "created_at"]


class CardSerializer(serializers.ModelSerializer):
    participant_name = serializers.CharField(source="ticket.participant_name", read_only=True, default=None)
    is_child = serializers.BooleanField(source="ticket.is_child", read_only=True, default=None)

    class Meta:
        model = Card
        fields = ["uid", "status", "balance", "linked_at", "participant_name", "is_child"]


class AdminCardListSerializer(serializers.ModelSerializer):
    participant_name = serializers.CharField(source="ticket.participant_name", read_only=True, default=None)

    class Meta:
        model = Card
        fields = ["id", "uid", "status", "balance", "linked_at", "participant_name", "created_at"]
