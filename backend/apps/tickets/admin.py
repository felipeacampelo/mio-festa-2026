from django.contrib import admin

from .models import Ticket, TicketAuditLog


class TicketAuditInline(admin.TabularInline):
    model = TicketAuditLog
    extra = 0
    readonly_fields = ("action", "actor", "note", "created_at")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_code", "participant_name", "participant_email", "status", "order", "checked_in_at")
    search_fields = ("participant_name", "participant_email", "ticket_code", "order__buyer_email", "order__public_id", "order__order_code")
    inlines = [TicketAuditInline]


@admin.register(TicketAuditLog)
class TicketAuditLogAdmin(admin.ModelAdmin):
    list_display = ("ticket", "action", "actor", "created_at")
