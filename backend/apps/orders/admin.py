from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("public_id", "buyer_name", "buyer_email", "quantity", "payment_method", "status", "created_at")
    search_fields = ("buyer_name", "buyer_email", "public_id")
