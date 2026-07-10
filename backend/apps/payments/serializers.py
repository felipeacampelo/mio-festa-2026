from rest_framework import serializers

from .models import Payment


class PaymentWebhookSerializer(serializers.Serializer):
    event = serializers.CharField(required=False)
    payment = serializers.DictField(required=False)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
