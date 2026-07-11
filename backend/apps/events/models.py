from django.db import models
from django.utils import timezone


class EventSettings(models.Model):
    name = models.CharField(max_length=255, default="Festa Junina da Igreja")
    slug = models.SlugField(unique=True, default="festa-junina")
    description = models.TextField(blank=True)
    event_date = models.DateTimeField(default=timezone.now)
    location = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sales_end_at = models.DateTimeField(null=True, blank=True)
    capacity_total = models.PositiveIntegerField(default=0, help_text="0 significa sem limite")
    no_refund_policy = models.TextField(default="Nao ha reembolso.")
    is_sales_paused = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuracao do Evento"
        verbose_name_plural = "Configuracoes do Evento"

    def __str__(self) -> str:
        return self.name

    @classmethod
    def get_solo(cls) -> "EventSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def sales_closed_by_date(self) -> bool:
        return bool(self.sales_end_at and timezone.now() >= self.sales_end_at)

    def paid_capacity_reached(self) -> bool:
        if not self.capacity_total:
            return False
        return self.paid_tickets_count() >= self.capacity_total

    def paid_tickets_count(self) -> int:
        from apps.tickets.models import Ticket

        return Ticket.objects.filter(status__in=[Ticket.Status.ACTIVE, Ticket.Status.USED]).count()

    def has_paid_capacity_for(self, quantity: int) -> bool:
        if not self.capacity_total:
            return True
        return self.paid_tickets_count() + quantity <= self.capacity_total

    def sales_status(self) -> str:
        if self.is_sales_paused:
            return "paused"
        if self.sales_closed_by_date:
            return "ended_by_date"
        if self.paid_capacity_reached():
            return "sold_out"
        return "open"
