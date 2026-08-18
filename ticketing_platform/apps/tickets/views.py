from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts.decorators import organizer_required
from apps.events.models import Event

from .forms import AddToCartForm, TicketTypeForm
from .models import Reservation, TicketType
from .services import RESERVATION_LOCK_MINUTES, reserve_tickets


# --- Attendee cart ---------------------------------------------------------

def cart(request):
    reservations = (
        Reservation.objects.filter(
            user=request.user,
            status=Reservation.Status.ACTIVE,
            expires_at__gt=timezone.now(),
        )
        .select_related("ticket_type__event__venue")
        .order_by("expires_at")
    )
    return render(request, "tickets/cart.html", {"reservations": reservations})


def add_to_cart(request):
    if request.method != "POST":
        return redirect("events:home")

    form = AddToCartForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid ticket selection.")
        return redirect("events:home")

    ticket_type = form.cleaned_data["ticket_type"]
    quantity = form.cleaned_data["quantity"]

    if not request.user.is_authenticated:
        next_url = reverse("events:public_event_detail", args=[ticket_type.event_id])
        if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(
                f"{reverse('accounts:login')}?next={next_url}"
            )
        return redirect("accounts:login")

    try:
        reservation = reserve_tickets(
            ticket_type.pk, request.user, quantity
        )
        messages.success(
            request,
            f"{reservation.quantity} × {reservation.ticket_type.name} held "
            f"for {RESERVATION_LOCK_MINUTES} minutes. Complete checkout before "
            "it expires.",
        )
    except ValidationError as exc:
        for error in exc.messages:
            messages.error(request, error)

    return redirect("events:public_event_detail", pk=ticket_type.event_id)


@login_required(login_url="accounts:login")
def remove_from_cart(request, pk):
    if request.method == "POST":
        Reservation.objects.filter(
            pk=pk,
            user=request.user,
            status=Reservation.Status.ACTIVE,
        ).delete()
        messages.success(request, "Removed from cart.")
    return redirect("tickets:cart")


# --- Organizer: Ticket tiers -----------------------------------------------

@organizer_required
def ticket_type_create(request, event_pk):
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)
    used_capacity = TicketType.allocated_total(event)
    if request.method == "POST":
        form = TicketTypeForm(request.POST)
        form.instance.event = event
        if form.is_valid():
            ticket_type = form.save(commit=False)
            ticket_type.save()
            messages.success(request, f"Ticket tier '{ticket_type.name}' created.")
            return redirect("events:organizer_event_detail", pk=event.pk)
    else:
        form = TicketTypeForm()
    return render(
        request,
        "tickets/ticket_type_form.html",
        {
            "form": form,
            "title": f"Add ticket tier to {event.name}",
            "event": event,
            "used_capacity": used_capacity,
        },
    )


@organizer_required
def ticket_type_update(request, pk):
    ticket_type = get_object_or_404(
        TicketType, pk=pk, event__organizer=request.user
    )
    used_capacity = TicketType.allocated_total(ticket_type.event)
    if request.method == "POST":
        form = TicketTypeForm(request.POST, instance=ticket_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ticket tier '{ticket_type.name}' updated.")
            return redirect(
                "events:organizer_event_detail", pk=ticket_type.event_id
            )
    else:
        form = TicketTypeForm(instance=ticket_type)
    return render(
        request,
        "tickets/ticket_type_form.html",
        {
            "form": form,
            "title": f"Edit {ticket_type.name}",
            "event": ticket_type.event,
            "used_capacity": used_capacity,
        },
    )


@organizer_required
def ticket_type_delete(request, pk):
    ticket_type = get_object_or_404(
        TicketType, pk=pk, event__organizer=request.user
    )
    if request.method == "POST":
        event_pk = ticket_type.event_id
        name = ticket_type.name
        ticket_type.delete()
        messages.success(request, f"Ticket tier '{name}' deleted.")
        return redirect("events:organizer_event_detail", pk=event_pk)
    return render(
        request,
        "tickets/ticket_type_confirm_delete.html",
        {"ticket_type": ticket_type},
    )