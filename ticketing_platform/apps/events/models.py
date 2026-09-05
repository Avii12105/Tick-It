from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class WaitlistEntry(models.Model):
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        PROMOTED = "promoted", "Promoted"

    event = models.ForeignKey(
        "Event",
        on_delete=models.CASCADE,
        related_name="waitlist_entries",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="waitlist_entries",
    )
    email = models.CharField(max_length=254)
    full_name = models.CharField(max_length=200)
    ticket_type = models.ForeignKey(
        "tickets.TicketType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="waitlist_entries",
    )
    position = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WAITING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("position",)
        unique_together = ("event", "email")

    def __str__(self):
        return f"{self.full_name} ({self.email}) - {self.event.name}"


class Venue(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    max_capacity = models.PositiveIntegerField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="venues",
    )
    image = models.ImageField(upload_to="venues/", blank=True, null=True)
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
    image = models.ImageField(upload_to="events/", blank=True, null=True)
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

    def promote_next(self):
        """Promote the first waitlist entry if capacity permits."""
        from apps.tickets.models import TicketType

        # Find the first waiting waitlist entry
        entry = self.waitlist_entries.filter(
            status=WaitlistEntry.Status.WAITING
        ).order_by("position").first()

        if not entry:
            return None

        # Check if there's an available ticket type with capacity
        ticket_types = self.ticket_types.filter(
            quantity_sold__lt=F("quantity_total")
        )

        if not ticket_types.exists():
            return None

        # Allocate a ticket from the first available tier
        ticket_type = ticket_types.first()

        # Create the ticket directly
        from apps.tickets.services import generate_unique_code
        from django.db import transaction
        import qrcode
        from io import BytesIO
        from django.core.files.base import ContentFile

        code = generate_unique_code()
        ticket = Ticket(
            ticket_type=ticket_type,
            event=self,
            user=entry.user,
            unique_code=code,
            status=Ticket.Status.ACTIVE,
        )
        ticket.save()
        # Generate QR code
        img = qrcode.make(code)
        buf = BytesIO()
        img.save(buf, format="PNG")
        ticket.qr_image.save(f"{code}.png", ContentFile(buf.getvalue()), save=True)

        # Mark the waitlist entry as promoted
        entry.status = WaitlistEntry.Status.PROMOTED
        entry.save()

        return entry