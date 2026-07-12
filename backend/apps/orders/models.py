import secrets
import string
import uuid

from django.db import models


def generate_access_token() -> str:
    return secrets.token_urlsafe(24)


def generate_order_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "MIO-" + "".join(secrets.choice(alphabet) for _ in range(6))


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Pago"
        CANCELLED = "cancelled", "Cancelado"
        EXPIRED = "expired", "Expirado"

    class PaymentMethod(models.TextChoices):
        PIX = "pix", "PIX"
        CREDIT_CARD = "credit_card", "Cartao"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order_code = models.CharField(max_length=10, default=generate_order_code, unique=True, editable=False)
    access_token = models.CharField(max_length=40, default=generate_access_token, editable=False)
    buyer_name = models.CharField(max_length=255)
    buyer_email = models.EmailField()
    buyer_phone = models.CharField(max_length=40, blank=True)
    buyer_document = models.CharField(max_length=14)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    accepted_no_refund = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.buyer_name} - {self.order_code}"

    @classmethod
    def lookup_filter(cls, code: str) -> models.Q:
        filters = models.Q(order_code__iexact=code)
        try:
            filters |= models.Q(public_id=uuid.UUID(code))
        except ValueError:
            pass
        return filters
