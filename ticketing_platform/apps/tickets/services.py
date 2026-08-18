from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Reservation, TicketType

from apps.events.models import Event

RESERVATION_LOCK_MINUTES = 10


def reserve_tickets(ticket_type_id, user, quantity):
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1.")

    with transaction.atomic():
        # Acquire the SQLite write lock *before* reading availability.
        # select_for_update() is a no-op on SQLite (no row locks), so without
        # this the file-level write lock is only taken at COMMIT time and two
        # concurrent adds could both read the same stale availability and
        # oversell. A no-op UPDATE takes the RESERVED lock immediately, which
        # serializes concurrent reserves on the same tier.
        TicketType.objects.filter(pk=ticket_type_id).update(
            quantity_sold=F("quantity_sold")
        )
        ticket_type = TicketType.objects.select_for_update().get(pk=ticket_type_id)

        if ticket_type.event.status != Event.Status.PUBLISHED:
            raise ValidationError(
                "Tickets are not available for this event yet."
            )

        available = ticket_type.available_count()
        if quantity > available:
            raise ValidationError(
                f"Only {available} ticket(s) left for {ticket_type.name}."
            )

        return Reservation.objects.create(
            ticket_type=ticket_type,
            user=user,
            quantity=quantity,
            expires_at=timezone.now()
            + timedelta(minutes=RESERVATION_LOCK_MINUTES),
            status=Reservation.Status.ACTIVE,
        )