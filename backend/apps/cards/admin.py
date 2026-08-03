from django.contrib import admin

from .models import Card, CardTransaction, Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ["display_name", "role", "is_active", "user"]
    list_filter = ["role", "is_active"]
    search_fields = ["display_name", "user__username"]


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ["uid", "status", "balance", "ticket", "linked_at"]
    list_filter = ["status"]
    search_fields = ["uid", "ticket__participant_name", "ticket__participant_document"]


@admin.register(CardTransaction)
class CardTransactionAdmin(admin.ModelAdmin):
    list_display = ["card", "type", "amount", "balance_after", "vendor", "created_at"]
    list_filter = ["type"]
    search_fields = ["card__uid", "idempotency_key"]
