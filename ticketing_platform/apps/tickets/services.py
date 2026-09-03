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


def checkin_ticket(qr_code, event_id, staff_user):
    """Check in a single ticket by its unique QR code.
    
    Args:
        qr_code: The ticket's unique_code value
        event_id: The event ID to verify ticket belongs to
        staff_user: The user performing the check-in
    
    Returns:
        dict with keys: status, ticket_id (if checked in), message
        Possible statuses: checked_in, already_checked_in, invalid_qr, wrong_event, ticket_not_eligible
    """
    now = timezone.now()
    
    with transaction.atomic():
        # Step 1: Attempt atomic conditional check-in directly
        # The WHERE clause ensures this only succeeds if checked_in_at is NULL
        # This is the primary concurrency prevention mechanism - database-enforced
        rows_updated = Ticket.objects.filter(
            unique_code=qr_code,
            event_id=event_id,
            checked_in_at__isnull=True,
        ).update(
            checked_in_at=now,
            checked_in_by=staff_user,
        )
        
        # Step 2: Check result and generate appropriate response
        if rows_updated == 1:
            # Check-in succeeded - ticket is now marked as checked in
            ticket = Ticket.objects.get(unique_code=qr_code, event_id=event_id)
            return {
                "status": "checked_in",
                "ticket_id": str(ticket.pk),
                "checked_in_at": ticket.checked_in_at.isoformat() if ticket.checked_in_at else None,
                "checked_in_by": str(ticket.checked_in_by) if ticket.checked_in_by else None,
            }
        else:
            # Affected rows = 0 means either:
            # (a) Ticket was already checked in by a concurrent request, or
            # (b) Ticket doesn't exist or doesn't belong to this event
            # Step 2a: Check if the ticket exists at all
            ticket = Ticket.objects.filter(unique_code=qr_code).first()
            if ticket is None:
                # Ticket doesn't exist in the system
                return {"status": "invalid_qr", "message": "QR code not found or does not belong to this event"}
            
            # Step 2b: Ticket exists but belongs to a different event
            if ticket.event_id != event_id:
                return {"status": "wrong_event", "message": "Ticket belongs to another event"}
            
            # Step 2c: Ticket exists and is for this event, but already checked in
            return {
                "status": "already_checked_in",
                "ticket_id": str(ticket.pk),
                "message": "Ticket has already been checked in",
            }


def bulk_checkin_tickets(qr_codes, event_id, staff_user):
    """Bulk check-in multiple tickets by their QR codes.
    
    Args:
        qr_codes: List of unique_code strings to check in
        event_id: The event ID all tickets must belong to
        staff_user: The user performing the check-ins
    
    Returns:
        dict with keys: results (list of per-QR results), total_processed
        Each result has: qr_code, status, ticket_id (if applicable), message
        Possible statuses: checked_in, already_checked_in, invalid_qr, wrong_event, ticket_not_eligible, duplicate_in_request
    """
    from django.db import transaction as db_transaction
    
    now = timezone.now()
    max_batch_size = 100
    
    # Validate input
    if not isinstance(qr_codes, list):
        return {
            "results": [
                {"qr_code": "invalid", "status": "invalid_qr", "message": "qr_codes must be an array"}
            ],
            "total_processed": 1,
        }
    
    if len(qr_codes) == 0:
        return {
            "results": [],
            "total_processed": 0,
        }
    
    if len(qr_codes) > max_batch_size:
        return {
            "results": [
                {"qr_code": qr, "status": "batch_too_large", "message": f"Batch exceeds maximum of {max_batch_size} QR codes"}
            ],
            "total_processed": 1,
        }
    
    # Deduplicate within request - track first occurrence
    seen = set()
    unique_qr_codes = []
    duplicate_flags = {}  # qr_code -> is_duplicate
    for code in qr_codes:
        if code in seen:
            duplicate_flags[code] = True
        else:
            seen.add(code)
            duplicate_flags[code] = False
            unique_qr_codes.append(code)
    
    results = [None] * len(qr_codes)
    
    with db_transaction.atomic():
        # Step 1: Fetch all matching tickets in a single query
        # Only fetch tickets for this event with matching unique codes
        fetched_tickets = Ticket.objects.filter(
            unique_code__in=unique_qr_codes,
            event_id=event_id,
        ).select_related("ticket_type", "event")
        
        # Build lookup: unique_code -> ticket
        ticket_map = {t.unique_code: t for t in fetched_tickets}
        
        # Track which QR codes we've already processed (for dedup within batch)
        processed_qr_codes = set()
        
        # Step 2: Process each unique QR code
        for i, qr_code in enumerate(unique_qr_codes):
            # Check if this QR code appeared multiple times in the request
            if duplicate_flags.get(qr_code, False):
                # This is a duplicate within the same batch
                # Find all positions where this QR code appears
                for pos, code in enumerate(qr_codes):
                    if code == qr_code:
                        if pos == 0:
                            # First occurrence - already processed above
                            pass
                        else:
                            # Subsequent duplicates
                            results[pos] = {
                                "qr_code": qr_code,
                                "status": "duplicate_in_request",
                                "message": "Duplicate QR code within same request",
                            }
            
            # Skip if already processed (shouldn't happen due to dedup, but safety)
            if qr_code in processed_qr_codes:
                continue
            processed_qr_codes.add(qr_code)
            
            # Step 3: Validate QR code exists and belongs to event
            if qr_code not in ticket_map:
                # QR code doesn't exist or belongs to different event
                # Map original positions to results
                for pos, code in enumerate(qr_codes):
                    if code == qr_code:
                        results[pos] = {
                            "qr_code": qr_code,
                            "status": "invalid_qr",
                            "message": "QR code not found or does not belong to this event",
                        }
                continue
            
            ticket = ticket_map[qr_code]
            
            # Step 4: Check ticket eligibility
            if ticket.status != Ticket.Status.ACTIVE:
                for pos, code in enumerate(qr_codes):
                    if code == qr_code:
                        results[pos] = {
                            "qr_code": qr_code,
                            "status": "ticket_not_eligible",
                            "message": "Ticket is not available for check-in",
                        }
                continue
            
            # Step 5: Atomic conditional check-in
            # This is the key concurrency prevention mechanism
            rows_updated = Ticket.objects.filter(
                pk=ticket.pk,
                checked_in_at__isnull=True,
            ).update(
                checked_in_at=now,
                checked_in_by=staff_user,
            )
            
            # Step 6: Record result based on affected rows
            if rows_updated == 1:
                # Check-in succeeded
                ticket.refresh_from_db()
                for pos, code in enumerate(qr_codes):
                    if code == qr_code:
                        results[pos] = {
                            "qr_code": qr_code,
                            "status": "checked_in",
                            "ticket_id": str(ticket.pk),
                            "message": "Ticket checked in successfully",
                        }
            else:
                # Affected rows = 0 means already checked in
                ticket.refresh_from_db()
                if ticket.checked_in_at is not None:
                    for pos, code in enumerate(qr_codes):
                        if code == qr_code:
                            results[pos] = {
                                "qr_code": qr_code,
                                "status": "already_checked_in",
                                "ticket_id": str(ticket.pk),
                                "message": "Ticket has already been checked in",
                            }
                else:
                    for pos, code in enumerate(qr_codes):
                        if code == qr_code:
                            results[pos] = {
                                "qr_code": qr_code,
                                "status": "already_checked_in",
                                "message": "Ticket was concurrently checked in",
                            }
    
    # Step 7: Fill in any unprocessed positions (shouldn't happen, but safety)
    for i, qr_code in enumerate(qr_codes):
        if results[i] is None:
            results[i] = {
                "qr_code": qr_code,
                "status": "processing_error",
                "message": "Failed to process this QR code",
            }
    
    return {
        "results": results,
        "total_processed": len(qr_codes),
    }