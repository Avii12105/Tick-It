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
        form = VenueForm(request.POST, request.FILES)
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
        form = VenueForm(request.POST, request.FILES, instance=venue)
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
        form = EventForm(request.POST, request.FILES, organizer=request.user)
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
        form = EventForm(request.POST, request.FILES, instance=event, organizer=request.user)
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


# V5: Bulk Import

from django.views.generic.edit import FormView
from django.urls import reverse, reverse_lazy

from .forms import BulkImportForm
from .models import Event, WaitlistEntry


class BulkImportView(FormView):
    template_name = "events/bulk_import.html"
    form_class = BulkImportForm

    def dispatch(self, request, *args, **kwargs):
        self.event = get_object_or_404(
            Event, pk=kwargs["pk"], organizer=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("events:organizer_event_detail", kwargs={"pk": self.event.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["initial"] = {"event_pk": self.event.pk}
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["event"] = self.event
        return kwargs

    def form_valid(self, form):
        csv_file = form.cleaned_data["csv_file"]
        csv_content = csv_file.read().decode("utf-8")
        from .tasks import process_bulk_import

        results = process_bulk_import(self.event.pk, csv_content)

        messages.success(
            self.request,
            f"Bulk import complete: {results['allocated']} tickets allocated, "
            f"{results['waitlisted']} added to waitlist, "
            f"{len(results['errors'])} errors.",
        )
        return super().form_valid(form)


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
    """Single QR code validation, check-in, and check-in page rendering.
    
    GET /events/{event_pk}/checkin/
    POST /events/{event_pk}/checkin/
    """
    event = get_object_or_404(Event, pk=event_pk)

    authorized, error = _check_authorize_event(request, event)
    if error:
        if request.method == "GET":
            messages.error(request, "You are not authorized to check-in tickets for this event.")
            return redirect("events:organizer_event_detail", pk=event.pk)
        return error

    # 1. Handle GET request: Render the check-in UI
    if request.method == "GET":
        return render(request, "events/checkin.html", {"event": event})

    # 2. Handle POST request: Process the QR Code payload
    import json
    try:
        body = json.loads(request.body)
        qr_code = body.get("qr_code", "").strip() if body else ""
    except json.JSONDecodeError:
        qr_code = request.POST.get("qr_code", "").strip()

    is_json_request = request.content_type == "application/json"

    if not qr_code:
        if is_json_request:
            return JsonResponse({"error": "QR code is required"}, status=400)
        messages.error(request, "QR code is required.")
        return redirect(request.path)

    from apps.tickets.services import checkin_ticket
    result = checkin_ticket(qr_code, event_pk, request.user)
    
    # Return JSON if triggered by JavaScript fetch()
    if is_json_request:
        return JsonResponse(result, status=200 if result.get("status") == "checked_in" else 400)
    
    # Return standard redirect if triggered by HTML form submission
    if result.get("status") == "checked_in":
        messages.success(request, result.get("message", "Ticket checked in successfully."))
    else:
        messages.error(request, result.get("message", "Validation failed."))
    
    return redirect(request.path)


@login_required
def checkin_bulk(request, event_pk):
    """Bulk QR code validation and check-in.
    
    POST /events/{event_pk}/checkin/bulk/
    """
    event = get_object_or_404(Event, pk=event_pk)

    authorized, error = _check_authorize_event(request, event)
    if error:
        if request.method == "GET":
            messages.error(request, "You are not authorized to check-in tickets for this event.")
            return redirect("events:organizer_event_detail", pk=event.pk)
        return error

    # Gracefully redirect browser GET requests back to the check-in UI
    if request.method == "GET":
        # Adjust the redirect string if your URL name is different
        return redirect("events:checkin_single", event_pk=event.pk)

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