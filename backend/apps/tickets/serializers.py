from rest_framework import serializers

from apps.orders.serializers import OrderSerializer
from apps.tickets.models import Ticket, TicketAuditLog
from apps.tickets.services import build_ticket_qr_data_url


class TicketAuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.SerializerMethodField()

    class Meta:
        model = TicketAuditLog
        fields = ["id", "action", "note", "created_at", "actor_username"]

    def get_actor_username(self, obj):
        return obj.actor.username if obj.actor else None


class AdminTicketSerializer(serializers.ModelSerializer):
    qr_code_data_url = serializers.SerializerMethodField()
    audit_logs = TicketAuditLogSerializer(many=True, read_only=True)
    order = OrderSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "ticket_code",
            "participant_name",
            "participant_email",
            "status",
            "checked_in_at",
            "superseded_by_ticket",
            "qr_code_data_url",
            "order",
            "audit_logs",
        ]

    def get_qr_code_data_url(self, obj):
        if obj.status not in [Ticket.Status.ACTIVE, Ticket.Status.USED]:
            return None
        return build_ticket_qr_data_url(obj)


class AdminTicketUpdateSerializer(serializers.Serializer):
    participant_name = serializers.CharField(max_length=255)
    participant_email = serializers.EmailField(required=False, allow_blank=True)


class AdminTicketTransferSerializer(AdminTicketUpdateSerializer):
    pass
