from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.events.models import Event


class TicketType(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="ticket_types",
    )
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_total = models.PositiveIntegerField()
    quantity_sold = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("price", "name")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_sold__lte=models.F("quantity_total")),
                name="tickettype_sold_lte_total",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.event.name})"

    def reserved_count(self):
        return self.reservations.filter(
            status=Reservation.Status.ACTIVE,
            expires_at__gt=timezone.now(),
        ).aggregate(total=Coalesce(Sum("quantity"), 0))["total"]

    def available_count(self):
        return self.quantity_total - self.quantity_sold - self.reserved_count()

    def clean(self):
        super().clean()
        validate_ticket_type_capacity(self)

    @classmethod
    def allocated_total(cls, event):
        return cls.objects.filter(event=event).aggregate(
            total=Coalesce(Sum("quantity_total"), 0)
        )["total"]


class Reservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CONVERTED = "converted", "Converted"

    ticket_type = models.ForeignKey(
        TicketType,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    quantity = models.PositiveIntegerField()
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} x{self.quantity} {self.ticket_type}"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE and self.expires_at > timezone.now()


def validate_ticket_type_capacity(ticket_type):
    if not ticket_type.quantity_total or not ticket_type.event_id:
        return
    if ticket_type.quantity_total < ticket_type.quantity_sold:
        raise ValidationError(
            {
                "quantity_total": (
                    "Cannot be less than the number already sold "
                    f"({ticket_type.quantity_sold})."
                )
            }
        )
    other = ticket_type.event.ticket_types.all()
    if ticket_type.pk:
        other = other.exclude(pk=ticket_type.pk)
    other_total = other.aggregate(total=Coalesce(Sum("quantity_total"), 0))["total"]
    total = ticket_type.quantity_total + other_total
    if total > ticket_type.event.allocated_capacity:
        raise ValidationError(
            {
                "quantity_total": (
                    f"Ticket allocation across tiers would be {total}, exceeding "
                    f"the event's allocated capacity of "
                    f"{ticket_type.event.allocated_capacity}."
                )
            }
        )