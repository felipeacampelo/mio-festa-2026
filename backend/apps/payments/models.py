from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        CONFIRMED = "confirmed", "Confirmado"
        CANCELLED = "cancelled", "Cancelado"
        EXPIRED = "expired", "Expirado"

    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="payment")
    external_id = models.CharField(max_length=120, blank=True)
    method = models.CharField(max_length=20, choices=[("pix", "PIX"), ("credit_card", "Cartao")])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    checkout_url = models.URLField(blank=True)
    pix_copy_paste = models.TextField(blank=True)
    pix_qr_code = models.TextField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.order.public_id} - {self.method} - {self.status}"
