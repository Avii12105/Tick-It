from django.contrib import admin

from .models import Event, Venue


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "max_capacity", "owner", "created_at")
    list_filter = ("owner",)
    search_fields = ("name", "address")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "venue",
        "allocated_capacity",
        "date",
        "status",
        "organizer",
    )
    list_filter = ("status", "venue")
    search_fields = ("name", "description")
    list_select_related = ("venue", "organizer")