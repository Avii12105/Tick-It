from django.contrib import admin

from .models import Reservation, TicketType


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "event",
        "price",
        "quantity_total",
        "quantity_sold",
        "available",
    )
    list_filter = ("event",)
    search_fields = ("name", "event__name")

    @admin.display(description="Available")
    def available(self, obj):
        return obj.available_count()


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "ticket_type",
        "quantity",
        "expires_at",
        "status",
        "created_at",
    )
    list_filter = ("status", "ticket_type__event")
    search_fields = ("user__username", "ticket_type__name")