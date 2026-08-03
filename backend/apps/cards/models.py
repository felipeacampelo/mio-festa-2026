from django.conf import settings
from django.db import models
from django.utils import timezone


class Vendor(models.Model):
    class Role(models.TextChoices):
        SELLER = "seller", "Vendedor"
        RECHARGE = "recharge", "Caixa de recarga"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendor_profile")
    role = models.CharField(max_length=20, choices=Role.choices)
    display_name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.display_name} ({self.get_role_display()})"


class Card(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        BLOCKED = "blocked", "Bloqueado"
        RETURNED = "returned", "Devolvido"

    uid = models.CharField(max_length=64, unique=True, db_index=True)
    ticket = models.OneToOneField(
        "tickets.Ticket", null=True, blank=True, on_delete=models.SET_NULL, related_name="card"
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    linked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.uid

    @property
    def is_linked(self) -> bool:
        return self.ticket_id is not None


class CardTransaction(models.Model):
    class Type(models.TextChoices):
        LINK = "link", "Vinculado"
        DEBIT = "debit", "Debito"
        DEBIT_FAILED = "debit_failed", "Debito recusado"
        CREDIT = "credit", "Credito"
        BLOCK = "block", "Bloqueado"
        UNBLOCK = "unblock", "Desbloqueado"
        RETURN = "return", "Devolvido"

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="transactions")
    type = models.CharField(max_length=20, choices=Type.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.card_id} - {self.type}"
