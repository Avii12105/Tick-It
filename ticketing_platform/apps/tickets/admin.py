from django.contrib import admin

from .models import Reservation, Ticket, TicketType


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


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "unique_code",
        "user",
        "ticket_type",
        "event",
        "status",
        "purchased_at",
    )
    list_filter = ("status", "event")
    search_fields = ("unique_code", "user__username")