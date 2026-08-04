from decimal import Decimal

from rest_framework import serializers

from apps.tickets.models import Ticket

from .models import Card, CardTransaction, Vendor


class VendorLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class CardAmountSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    idempotency_key = serializers.CharField(max_length=64)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class CardLinkSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField()
    include_consumption = serializers.BooleanField(default=True)


class TicketSearchResultSerializer(serializers.ModelSerializer):
    order_buyer_name = serializers.CharField(source="order.buyer_name", read_only=True)
    has_card = serializers.SerializerMethodField()

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
        ]

    def get_has_card(self, obj: Ticket) -> bool:
        return Card.objects.filter(ticket=obj).exists()


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
