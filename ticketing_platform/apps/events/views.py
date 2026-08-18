from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import organizer_required
from apps.tickets.models import TicketType

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