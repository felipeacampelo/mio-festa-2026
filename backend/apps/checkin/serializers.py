from rest_framework import serializers


class CheckinScanSerializer(serializers.Serializer):
    qr_token = serializers.CharField()


class ManualCheckinSerializer(serializers.Serializer):
    ticket_code = serializers.CharField()
