from django.contrib import admin

from .models import Card, CardTransaction, CardTransactionItem, Product, Vendor


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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "vendor", "price", "is_active", "updated_at"]
    list_filter = ["is_active", "vendor"]
    search_fields = ["name", "vendor__display_name"]


@admin.register(CardTransactionItem)
class CardTransactionItemAdmin(admin.ModelAdmin):
    list_display = ["transaction", "product_name", "unit_price", "quantity"]
    search_fields = ["product_name", "transaction__card__uid"]
