from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import JsonResponse

from apps.accounts.decorators import organizer_required
from apps.tickets.models import Ticket, TicketType

from .forms import EventForm, VenueForm
from .models import Event, Venue


# --- Public views -----------------------------------------------------------

def home(request):
    events = Event.objects.filter(status=Event.Status.PUBLISHED)
    return render(request, "events/event_list.html", {"events": events})


def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk, status=Event.Status.PUBLISHED)
    ticket_types = event.ticket_types.all()
    return render(
        request,
        "events/event_detail.html",
        {"event": event, "ticket_types": ticket_types},
    )


# --- Organizer: Venues ------------------------------------------------------

@organizer_required
def venue_list(request):
    venues = Venue.objects.filter(owner=request.user)
    return render(request, "events/venue_list.html", {"venues": venues})


@organizer_required
def venue_create(request):
    if request.method == "POST":
        form = VenueForm(request.POST)
        if form.is_valid():
            venue = form.save(commit=False)
            venue.owner = request.user
            venue.save()
            messages.success(request, f"Venue '{venue.name}' created.")
            return redirect("events:venue_detail", pk=venue.pk)
    else:
        form = VenueForm()
    return render(request, "events/venue_form.html", {"form": form, "title": "New Venue"})


@organizer_required
def venue_detail(request, pk):
    venue = get_object_or_404(Venue, pk=pk, owner=request.user)
    events = venue.events.all()
    return render(
        request,
        "events/venue_detail.html",
        {"venue": venue, "events": events},
    )


@organizer_required
def venue_update(request, pk):
    venue = get_object_or_404(Venue, pk=pk, owner=request.user)
    if request.method == "POST":
        form = VenueForm(request.POST, instance=venue)
        if form.is_valid():
            form.save()
            messages.success(request, f"Venue '{venue.name}' updated.")
            return redirect("events:venue_detail", pk=venue.pk)
    else:
        form = VenueForm(instance=venue)
    return render(
        request,
        "events/venue_form.html",
        {"form": form, "title": f"Edit {venue.name}"},
    )


@organizer_required
def venue_delete(request, pk):
    venue = get_object_or_404(Venue, pk=pk, owner=request.user)
    if request.method == "POST":
        name = venue.name
        venue.delete()
        messages.success(request, f"Venue '{name}' deleted.")
        return redirect("events:venue_list")
    return render(request, "events/venue_confirm_delete.html", {"venue": venue})


# --- Organizer: Events ------------------------------------------------------

@organizer_required
def organizer_event_list(request):
    events = Event.objects.filter(organizer=request.user).select_related("venue")
    return render(request, "events/organizer_event_list.html", {"events": events})


@organizer_required
def organizer_event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    ticket_types = event.ticket_types.all()
    used_capacity = TicketType.allocated_total(event)
    return render(
        request,
        "events/organizer_event_detail.html",
        {
            "event": event,
            "ticket_types": ticket_types,
            "used_capacity": used_capacity,
        },
    )


@organizer_required
def event_create(request):
    if request.method == "POST":
        form = EventForm(request.POST, organizer=request.user)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, f"Event '{event.name}' created.")
            return redirect("events:organizer_event_list")
    else:
        form = EventForm(organizer=request.user)
    return render(request, "events/event_form.html", {"form": form, "title": "New Event"})


@organizer_required
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    if request.method == "POST":
        form = EventForm(request.POST, instance=event, organizer=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Event '{event.name}' updated.")
            return redirect("events:organizer_event_list")
    else:
        form = EventForm(instance=event, organizer=request.user)
    return render(request, "events/event_form.html", {"form": form, "title": f"Edit {event.name}"})


@organizer_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    if request.method == "POST":
        name = event.name
        event.delete()
        messages.success(request, f"Event '{name}' deleted.")
        return redirect("events:organizer_event_list")
    return render(request, "events/event_confirm_delete.html", {"event": event})


# --- V4: Event Check-In ---


ORGANIZER_ROLE = "organizer"


def _check_authorize_event(request, event):
    """Verify user is organizer of the event.
    
    Returns (authorized: bool, error_response: JsonResponse|None)
    """
    if request.user.profile.role != ORGANIZER_ROLE:
        return False, JsonResponse(
            {"error": "Organizer role required"},
            status=403,
        )
    if event.organizer_id != request.user.id:
        return False, JsonResponse(
            {"error": "You are not authorized to check-in tickets for this event"},
            status=403,
        )
    return True, None


@login_required
def checkin_single(request, event_pk):
    """Single QR code validation and check-in.
    
    POST /events/{event_pk}/checkin/
    """
    event = get_object_or_404(Event, pk=event_pk)

    authorized, error = _check_authorize_event(request, event)
    if error:
        return error

    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    import json
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    qr_code = body.get("qr_code", "").strip() if body else ""
    if not qr_code:
        return JsonResponse({"error": "QR code is required"}, status=400)

    from apps.tickets.services import checkin_ticket

    result = checkin_ticket(qr_code, event_pk, request.user)
    return JsonResponse(result, status=200 if result.get("status") == "checked_in" else 400)


@login_required
def checkin_bulk(request, event_pk):
    """Bulk QR code validation and check-in.
    
    POST /events/{event_pk}/checkin/bulk/
    """
    event = get_object_or_404(Event, pk=event_pk)

    authorized, error = _check_authorize_event(request, event)
    if error:
        return error

    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    import json
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    qr_codes = body.get("qr_codes", [])
    if not isinstance(qr_codes, list) or len(qr_codes) == 0:
        return JsonResponse(
            {"error": "qr_codes array is required and must not be empty"},
            status=400,
        )
    if len(qr_codes) > 100:
        return JsonResponse(
            {"error": "Batch size exceeds maximum of 100 QR codes"},
            status=400,
        )

    from apps.tickets.services import bulk_checkin_tickets

    result = bulk_checkin_tickets(qr_codes, event_pk, request.user)
    return JsonResponse(result, status=200)