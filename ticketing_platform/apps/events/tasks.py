from io import BytesIO

import qrcode
from django.core.mail import send_mail
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.db import transaction

from .models import WaitlistEntry, Event
from apps.tickets.models import Ticket


def send_waitlist_promotion_email(entry):
    """Send email notification when a waitlist entry is promoted."""
    subject = f"Your waitlist entry has been promoted for {entry.event.name}"
    from_email = None
    recipient_list = [entry.email]
    context = {"entry": entry, "event": entry.event}
    message = render_to_string("emails/waitlist_promotion.html", context)
    send_mail(subject, message, from_email, recipient_list)


def generate_ticket_qr(ticket):
    """Generate and save QR code for a ticket."""
    img = qrcode.make(ticket.unique_code)
    buf = BytesIO()
    img.save(buf, format="PNG")
    ticket.qr_image.save(f"{ticket.unique_code}.png", ContentFile(buf.getvalue()), save=True)


def process_bulk_import(event_id, csv_content):
    """Process bulk import of VIP guests from CSV content.

    For each valid row, gets or creates an inactive user account keyed by
    email, then allocates a ticket directly. If no ticket type is specified,
    uses the first available type. Rows that exceed capacity are skipped with
    an error.
    """
    import csv
    from io import StringIO

    from django.contrib.auth import get_user_model
    from django.db import transaction as db_transaction
    from apps.tickets.services import generate_unique_code

    User = get_user_model()
    event = Event.objects.get(pk=event_id)

    reader = csv.DictReader(StringIO(csv_content))
    results = {
        "created": 0,
        "waitlisted": 0,
        "allocated": 0,
        "errors": [],
    }

    with db_transaction.atomic():
        for row_num, row in enumerate(reader, start=1):
            email = row.get("email", "").strip()
            full_name = row.get("full_name", "").strip()
            ticket_type_name = row.get("ticket_type", "").strip()

            if not email or not full_name:
                results["errors"].append(
                    f"Row {row_num}: Missing email or full_name"
                )
                continue

            # Resolve ticket type
            ticket_type = None
            if ticket_type_name:
                try:
                    ticket_type = event.ticket_types.get(name=ticket_type_name)
                except Exception:
                    results["errors"].append(
                        f"Row {row_num}: Ticket type '{ticket_type_name}' not found"
                    )
                    continue
            else:
                # Pick the first type with availability
                ticket_type = next(
                    (tt for tt in event.ticket_types.all() if tt.available_count() > 0),
                    None,
                )
                if ticket_type is None:
                    results["errors"].append(
                        f"Row {row_num}: No ticket types with available capacity"
                    )
                    continue

            # Check capacity
            if ticket_type.available_count() <= 0:
                results["errors"].append(
                    f"Row {row_num}: No capacity left for ticket type '{ticket_type.name}'"
                )
                continue

            # Check for duplicate ticket
            if Ticket.objects.filter(event=event, user__email=email).exclude(
                status=Ticket.Status.REFUNDED
            ).exists():
                results["errors"].append(
                    f"Row {row_num}: Email '{email}' already has a ticket"
                )
                continue

            # Get or create an inactive placeholder account for this guest.
            # They can claim it later by signing up with the same email.
            first_name, _, last_name = full_name.partition(" ")
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_active": False,
                },
            )

            # Allocate ticket
            code = generate_unique_code()
            ticket = Ticket(
                ticket_type=ticket_type,
                event=event,
                user=user,
                unique_code=code,
                status=Ticket.Status.ACTIVE,
            )
            ticket.save()
            generate_ticket_qr(ticket)

            # Keep quantity_sold in sync
            ticket_type.quantity_sold += 1
            ticket_type.save(update_fields=["quantity_sold"])

            results["allocated"] += 1

    return results


def promote_waitlist_entry(entry_id):
    """Promote a single waitlist entry to an actual ticket.

    Converts a waitlist entry into an actual Ticket, sends email,
    and marks entry as promoted.
    """
    entry = WaitlistEntry.objects.get(pk=entry_id)
    event = entry.event

    with transaction.atomic():
        # Check if there's capacity
        ticket_types = event.ticket_types.filter(
            quantity_sold__lt=F("quantity_total")
        )

        if not ticket_types.exists():
            entry.status = WaitlistEntry.Status.WAITING
            entry.save()
            return False

        ticket_type = ticket_types.first()

        # Create the ticket
        code = generate_unique_code()
        ticket = Ticket(
            ticket_type=ticket_type,
            event=event,
            user=entry.user,
            unique_code=code,
            status=Ticket.Status.ACTIVE,
        )
        ticket.save()
        generate_ticket_qr(ticket)

        # Mark the waitlist entry as promoted
        entry.status = WaitlistEntry.Status.PROMOTED
        entry.save()

        # Send email notification
        send_waitlist_promotion_email(entry)

    return True


def handle_refund(ticket_id):
    """Handle ticket refund by promoting next waitlist entry.

    Called when a ticket is refunded; deletes ticket, then calls
    event.promote_next() via Celery.
    """
    ticket = Ticket.objects.get(pk=ticket_id)
    event = ticket.event

    with transaction.atomic():
        # Delete the ticket
        ticket.delete()

        # Promote next waitlist entry
        entry = event.promote_next()

    return entry