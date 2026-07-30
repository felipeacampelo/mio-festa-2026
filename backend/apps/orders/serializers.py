from decimal import Decimal
from datetime import date

from django.db import transaction
from rest_framework import serializers

from apps.events.models import EventSettings
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.services import PaymentService
from apps.tickets.models import Ticket
from apps.tickets.services import build_ticket_qr_data_url

CHILD_MAX_AGE = 6


class ParticipantSerializer(serializers.Serializer):
    participant_name = serializers.CharField(max_length=255)
    participant_email = serializers.EmailField(required=False, allow_blank=True)
    is_child = serializers.BooleanField(default=False)
    participant_document = serializers.CharField(max_length=20, required=False, allow_blank=True)
    participant_birth_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs.get("is_child"):
            doc = "".join(ch for ch in (attrs.get("participant_document") or "") if ch.isdigit())
            if len(doc) != 11:
                raise serializers.ValidationError(
                    {"participant_document": "Informe o CPF da criança (11 dígitos)."}
                )
            attrs["participant_document"] = doc
            birth = attrs.get("participant_birth_date")
            if not birth:
                raise serializers.ValidationError(
                    {"participant_birth_date": "Informe a data de nascimento da criança."}
                )
            today = date.today()
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            if age > CHILD_MAX_AGE:
                raise serializers.ValidationError(
                    {"participant_birth_date": f"Ingresso gratuito apenas para crianças de até {CHILD_MAX_AGE} anos."}
                )
        return attrs


class TicketSerializer(serializers.ModelSerializer):
    qr_code_data_url = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "ticket_code",
            "participant_name",
            "participant_email",
            "is_child",
            "participant_document",
            "participant_birth_date",
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
            "order_code",
            "buyer_name",
            "buyer_email",
            "buyer_phone",
            "buyer_document",
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
    buyer_document = serializers.CharField(max_length=20)
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices)
    accepted_no_refund = serializers.BooleanField()
    participants = ParticipantSerializer(many=True, min_length=1)

    def validate_buyer_document(self, value):
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) not in (11, 14):
            raise serializers.ValidationError("Informe um CPF (11 digitos) ou CNPJ (14 digitos) valido.")
        return digits

    def validate(self, attrs):
        event = EventSettings.get_solo()
        if event.sales_status() != "open":
            raise serializers.ValidationError("As vendas estao encerradas no momento.")
        if not event.has_paid_capacity_for(len(attrs.get("participants", []))):
            raise serializers.ValidationError("Nao ha vagas suficientes para a quantidade selecionada.")
        if not attrs["accepted_no_refund"]:
            raise serializers.ValidationError("E necessario aceitar a politica de nao reembolso.")
        attrs["event"] = event
        return attrs

    def create(self, validated_data):
        participants = validated_data.pop("participants")
        event = validated_data.pop("event")
        quantity = len(participants)
        unit_price = Decimal(str(event.price))
        paid_count = sum(1 for p in participants if not p.get("is_child"))
        total_amount = unit_price * paid_count
        with transaction.atomic():
            order = Order.objects.create(
                quantity=quantity,
                unit_price=unit_price,
                total_amount=total_amount,
                **validated_data,
            )
            from apps.tickets.services import append_audit
            from apps.tickets.models import TicketAuditLog

            for participant in participants:
                ticket = Ticket.objects.create(
                    order=order,
                    participant_name=participant["participant_name"],
                    participant_email=participant.get("participant_email", ""),
                    is_child=participant.get("is_child", False),
                    participant_document=participant.get("participant_document", ""),
                    participant_birth_date=participant.get("participant_birth_date"),
                    status=Ticket.Status.PENDING,
                )
                append_audit(ticket, TicketAuditLog.Action.CREATED, note="Ticket criado no checkout.")
            PaymentService().ensure_payment(order)
            return order
