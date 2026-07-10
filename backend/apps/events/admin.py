from django.contrib import admin

from .models import EventSettings


@admin.register(EventSettings)
class EventSettingsAdmin(admin.ModelAdmin):
    list_display = ("name", "event_date", "location", "price", "sales_end_at", "capacity_total", "is_sales_paused")
