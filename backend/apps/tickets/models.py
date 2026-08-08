import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Ticket(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        ACTIVE = "active", "Ativo"
        USED = "used", "Usado"
        CANCELLED = "cancelled", "Cancelado"
        REISSUED = "reissued", "Reemitido"

    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="tickets")
    ticket_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    participant_name = models.CharField(max_length=255)
    participant_email = models.EmailField(blank=True)
    is_child = models.BooleanField(default=False)
    participant_document = models.CharField(max_length=14, blank=True)
    participant_birth_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    superseded_by_ticket = models.OneToOneField("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replaces")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.participant_name} - {self.ticket_code}"

    @property
    def is_checkin_allowed(self) -> bool:
        return self.status == self.Status.ACTIVE


class TicketAuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Criado"
        ACTIVATED = "activated", "Ativado"
        EDITED = "edited", "Editado"
        TRANSFERRED = "transferred", "Transferido"
        REISSUED = "reissued", "Reemitido"
        CHECKED_IN = "checked_in", "Check-in"
        RESENT = "resent", "Reenviado"
        CHECKIN_UNDONE = "checkin_undone", "Check-in desfeito"

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=20, choices=Action.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.ticket_id} - {self.action}"
