from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Venue(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    max_capacity = models.PositiveIntegerField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="venues",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        validate_venue_capacity(self)


def validate_venue_capacity(venue):
    if (
        venue.pk
        and venue.events.filter(allocated_capacity__gt=venue.max_capacity).exists()
    ):
        raise ValidationError(
            {
                "max_capacity": (
                    "Cannot reduce capacity below an existing event's ticket "
                    "allocation."
                )
            }
        )


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CANCELLED = "cancelled", "Cancelled"

    venue = models.ForeignKey(
        Venue,
        on_delete=models.PROTECT,
        related_name="events",
    )
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="events",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    allocated_capacity = models.PositiveIntegerField(
        help_text="Total number of tickets this event will sell.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.allocated_capacity and self.venue_id:
            venue = self.venue
            if self.allocated_capacity > venue.max_capacity:
                raise ValidationError(
                    {
                        "allocated_capacity": (
                            f"Cannot exceed venue capacity of {venue.max_capacity}."
                        )
                    }
                )