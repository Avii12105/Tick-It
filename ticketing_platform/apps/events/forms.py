"""
Events forms — VenueForm, EventForm, and BulkImportForm.

VenueForm and EventForm are standard ModelForms with one key detail:
EventForm's venue queryset is scoped to the requesting organizer's venues
so a crafted POST referencing another organizer's venue ID is rejected at
the form level, not just hidden from the dropdown.
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import Event, Venue


class VenueForm(forms.ModelForm):
    """Simple form for creating/editing a venue. Owner is set in the view."""

    class Meta:
        model  = Venue
        fields = ("name", "address", "max_capacity")


class EventForm(forms.ModelForm):
    """
    Form for creating/editing an event.

    The venue field queryset is filtered to the organizer's own venues so:
      - The dropdown only shows venues the organizer owns.
      - A crafted POST with someone else's venue pk is rejected by Django's
        ModelChoiceField validation before the view logic even runs.
    """

    # Override the widget so browsers render a native datetime picker.
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    class Meta:
        model  = Event
        fields = (
            "venue",
            "name",
            "description",
            "date",
            "allocated_capacity",
            "status",
        )

    def __init__(self, *args, **kwargs):
        # organizer is passed from the view — not a model field, so we pop it
        # before calling super() to avoid Django complaining about an unknown kwarg.
        organizer = kwargs.pop("organizer", None)
        super().__init__(*args, **kwargs)
        if organizer is not None:
            # Scope venue choices to the organizer's own venues only.
            self.fields["venue"].queryset = Venue.objects.filter(owner=organizer)


class BulkImportForm(forms.Form):
    """
    Form for uploading a CSV of VIP guests (V5 bulk import).

    Accepts a CSV file with columns: email, full_name, ticket_type (optional).
    Validates size and content type before the view processes the rows.
    """

    csv_file = forms.FileField(
        label="CSV File",
        help_text="Max 5MB. Columns: email, full_name, ticket_type (optional).",
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get("csv_file")
        if csv_file:
            # Reject files over 5MB to prevent memory issues during parsing.
            if csv_file.size > 5 * 1024 * 1024:
                raise ValidationError("File must be under 5MB.")
            if csv_file.content_type != "text/csv":
                raise ValidationError("File must be a CSV.")
        return csv_file
