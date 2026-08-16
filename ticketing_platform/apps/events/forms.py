from django import forms

from .models import Event, Venue


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