from rest_framework import serializers

from .models import EventSettings


class EventSettingsSerializer(serializers.ModelSerializer):
    sales_status = serializers.SerializerMethodField()

    class Meta:
        model = EventSettings
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "event_date",
            "location",
            "price",
            "sales_end_at",
            "capacity_total",
            "no_refund_policy",
            "is_sales_paused",
            "sales_status",
        ]

    def get_sales_status(self, obj: EventSettings) -> str:
        return obj.sales_status()
