from django import forms
from django.core.exceptions import ValidationError

from .models import Event, Venue


class BulkImportForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Max 5MB. Columns: email, full_name, ticket_type (optional).",
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get("csv_file")
        if csv_file:
            # Check file size (5MB limit)
            if csv_file.size > 5 * 1024 * 1024:
                raise ValidationError("File must be under 5MB.")
            # Check content type
            if not csv_file.content_type == "text/csv":
                raise ValidationError("File must be a CSV.")
        return csv_file


class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ("name", "address", "max_capacity")


class EventForm(forms.ModelForm):
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    class Meta:
        model = Event
        fields = (
            "venue",
            "name",
            "description",
            "date",
            "allocated_capacity",
            "status",
        )

    def __init__(self, *args, **kwargs):
        organizer = kwargs.pop("organizer", None)
        super().__init__(*args, **kwargs)
        if organizer is not None:
            self.fields["venue"].queryset = Venue.objects.filter(owner=organizer)