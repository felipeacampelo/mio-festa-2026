from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.events.models import EventSettings
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.services import PaymentService
from apps.tickets.models import Ticket
from apps.tickets.services import build_ticket_qr_data_url


class ParticipantSerializer(serializers.Serializer):
    participant_name = serializers.CharField(max_length=255)
    participant_email = serializers.EmailField(required=False, allow_blank=True)


class TicketSerializer(serializers.ModelSerializer):
    qr_code_data_url = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "ticket_code",
            "participant_name",
            "participant_email",
            "status",
            "checked_in_at",
            "qr_code_data_url",
        ]

    def get_qr_code_data_url(self, obj: Ticket):
        if obj.status not in [Ticket.Status.ACTIVE, Ticket.Status.USED]:
            return None
        return build_ticket_qr_data_url(obj)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "external_id", "method", "status", "checkout_url", "pix_copy_paste", "pix_qr_code"]


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "public_id",
            "buyer_name",
            "buyer_email",
            "buyer_phone",
            "quantity",
            "unit_price",
            "total_amount",
            "accepted_no_refund",
            "payment_method",
            "status",
            "paid_at",
            "created_at",
            "tickets",
            "payment",
        ]


class OrderCreateSerializer(serializers.Serializer):
    buyer_name = serializers.CharField(max_length=255)
    buyer_email = serializers.EmailField()
    buyer_phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices)
    accepted_no_refund = serializers.BooleanField()
    participants = ParticipantSerializer(many=True, min_length=1)

    def validate(self, attrs):
        event = EventSettings.get_solo()
        if event.sales_status() != "open":
            raise serializers.ValidationError("As vendas estao encerradas no momento.")
        if not attrs["accepted_no_refund"]:
            raise serializers.ValidationError("E necessario aceitar a politica de nao reembolso.")
        attrs["event"] = event
        return attrs

    def create(self, validated_data):
        participants = validated_data.pop("participants")
        event = validated_data.pop("event")
        quantity = len(participants)
        unit_price = Decimal(str(event.price))
        with transaction.atomic():
            order = Order.objects.create(
                quantity=quantity,
                unit_price=unit_price,
                total_amount=unit_price * quantity,
                **validated_data,
            )
            for participant in participants:
                ticket = Ticket.objects.create(
                    order=order,
                    participant_name=participant["participant_name"],
                    participant_email=participant.get("participant_email", ""),
                    status=Ticket.Status.PENDING,
                )
                from apps.tickets.services import append_audit
                from apps.tickets.models import TicketAuditLog

                append_audit(ticket, TicketAuditLog.Action.CREATED, note="Ticket criado no checkout.")
            PaymentService().ensure_payment(order)
            return order
