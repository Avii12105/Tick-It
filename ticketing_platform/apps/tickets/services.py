from datetime import timedelta
from io import BytesIO
import secrets

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F
from django.utils import timezone
import qrcode

from .models import Reservation, Ticket, TicketType

from apps.events.models import Event

RESERVATION_LOCK_MINUTES = 10


def reserve_tickets(ticket_type_id, user, quantity):
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1.")

    with transaction.atomic():
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


def generate_unique_code():
    while True:
        code = secrets.token_urlsafe(24)
        if not Ticket.objects.filter(unique_code=code).exists():
            return code


def _create_ticket(ticket_type, user):
    code = generate_unique_code()
    ticket = Ticket(
        ticket_type=ticket_type,
        event=ticket_type.event,
        user=user,
        unique_code=code,
        status=Ticket.Status.ACTIVE,
    )
    ticket.save()
    img = qrcode.make(code)
    buf = BytesIO()
    img.save(buf, format="PNG")
    ticket.qr_image.save(f"{code}.png", ContentFile(buf.getvalue()), save=True)
    return ticket


def checkout_cart(user):
    now = timezone.now()
    reservations = list(
        Reservation.objects.filter(
            user=user,
            status=Reservation.Status.ACTIVE,
            expires_at__gt=now,
        ).select_related("ticket_type")
    )
    if not reservations:
        raise ValidationError("Your cart is empty or all holds have expired.")

    type_pks = sorted({r.ticket_type_id for r in reservations})
    with transaction.atomic():
        TicketType.objects.filter(pk__in=type_pks).update(
            quantity_sold=F("quantity_sold")
        )
        locked_types = {
            tt.pk: tt
            for tt in TicketType.objects.select_for_update().filter(
                pk__in=type_pks
            )
        }

        created_tickets = []
        for r in reservations:
            tt = locked_types[r.ticket_type_id]
            r.refresh_from_db()
            if r.status != Reservation.Status.ACTIVE or r.expires_at <= now:
                raise ValidationError(
                    "A reservation expired during checkout. Please try again."
                )
            if tt.quantity_sold + r.quantity > tt.quantity_total:
                raise ValidationError(
                    f"Not enough tickets left for {tt.name}."
                )
            r.status = Reservation.Status.CONVERTED
            r.save()
            tt.quantity_sold += r.quantity
            tt.save()
            for _ in range(r.quantity):
                ticket = _create_ticket(tt, user)
                created_tickets.append(ticket)

        return created_tickets