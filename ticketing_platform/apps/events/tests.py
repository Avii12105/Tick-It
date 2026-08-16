from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profile

from .models import Event, Venue

User = get_user_model()


def make_user(username, role):
    user = User.objects.create_user(username=username, password="pass12345")
    user.profile.role = role
    user.profile.save()
    return user


def event_data(**overrides):
    data = {
        "venue": None,
        "name": "Test Event",
        "description": "",
        "date": "2026-12-01T10:00",
        "allocated_capacity": 50,
        "status": "draft",
    }
    data.update(overrides)
    return data


class CapacityConstraintTests(TestCase):
    def setUp(self):
        self.org = make_user("org", Profile.Role.ORGANIZER)
        self.venue = Venue.objects.create(
            name="Stadium", max_capacity=100, owner=self.org
        )

    def test_clean_rejects_over_capacity(self):
        event = Event(
            venue=self.venue,
            organizer=self.org,
            name="X",
            date=datetime.now(timezone.utc),
            allocated_capacity=101,
        )
        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_save_signal_rejects_over_capacity(self):
        with self.assertRaises(ValidationError):
            Event.objects.create(
                venue=self.venue,
                organizer=self.org,
                name="X",
                date=datetime.now(timezone.utc),
                allocated_capacity=150,
            )

    def test_at_capacity_allowed(self):
        event = Event.objects.create(
            venue=self.venue,
            organizer=self.org,
            name="X",
            date=datetime.now(timezone.utc),
            allocated_capacity=100,
        )
        self.assertEqual(Event.objects.get(pk=event.pk).allocated_capacity, 100)

    def test_venue_cannot_shrink_below_existing_event_allocation(self):
        Event.objects.create(
            venue=self.venue,
            organizer=self.org,
            name="Full House",
            date=datetime.now(timezone.utc),
            allocated_capacity=100,
        )
        with self.assertRaises(ValidationError):
            self.venue.max_capacity = 50
            self.venue.save()

    def test_venue_shrink_allowed_when_events_fit(self):
        Event.objects.create(
            venue=self.venue,
            organizer=self.org,
            name="Half Full",
            date=datetime.now(timezone.utc),
            allocated_capacity=40,
        )
        self.venue.max_capacity = 50
        self.venue.save()
        self.assertEqual(
            Venue.objects.get(pk=self.venue.pk).max_capacity, 50
        )


class OrganizerFlowTests(TestCase):
    def setUp(self):
        self.org = make_user("org", Profile.Role.ORGANIZER)
        self.attendee = make_user("attendee", Profile.Role.ATTENDEE)
        self.venue = Venue.objects.create(
            name="Stadium", max_capacity=100, owner=self.org
        )

    def test_attendee_cannot_access_organizer_views(self):
        self.client.login(username="attendee", password="pass12345")
        response = self.client.get(reverse("events:venue_list"))
        self.assertRedirects(response, reverse("events:home"))

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("events:venue_list"))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next=/organizer/venues/")

    def test_organizer_creates_venue_and_event(self):
        self.client.login(username="org", password="pass12345")
        response = self.client.post(
            reverse("events:venue_create"),
            {"name": "Arena", "address": "Downtown", "max_capacity": 200},
        )
        arena = Venue.objects.get(name="Arena")
        self.assertRedirects(response, reverse("events:venue_detail", args=[arena.pk]))

        response = self.client.post(
            reverse("events:event_create"),
            event_data(venue=self.venue.pk, name="Concert", status="published"),
        )
        self.assertRedirects(response, reverse("events:organizer_event_list"))
        self.assertTrue(Event.objects.filter(name="Concert").exists())

    def test_event_over_capacity_form_rejected(self):
        self.client.login(username="org", password="pass12345")
        response = self.client.post(
            reverse("events:event_create"),
            event_data(venue=self.venue.pk, allocated_capacity=999),
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("allocated_capacity", form.errors)

    def test_organizer_cannot_edit_others_venue(self):
        other = make_user("other", Profile.Role.ORGANIZER)
        other_venue = Venue.objects.create(
            name="Other Hall", max_capacity=50, owner=other
        )
        self.client.login(username="org", password="pass12345")
        response = self.client.get(
            reverse("events:venue_detail", args=[other_venue.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_venue_shrink_below_event_form_rejected(self):
        Event.objects.create(
            venue=self.venue,
            organizer=self.org,
            name="Full House",
            date=datetime.now(timezone.utc),
            allocated_capacity=100,
        )
        self.client.login(username="org", password="pass12345")
        response = self.client.post(
            reverse("events:venue_update", args=[self.venue.pk]),
            {"name": "Stadium", "address": "", "max_capacity": 50},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("max_capacity", form.errors)


class PublicBrowseTests(TestCase):
    def setUp(self):
        self.org = make_user("org", Profile.Role.ORGANIZER)
        self.venue = Venue.objects.create(
            name="Stadium", max_capacity=100, owner=self.org
        )

    def test_home_shows_only_published(self):
        Event.objects.create(
            venue=self.venue,
            organizer=self.org,
            name="PublicEvent",
            date=datetime.now(timezone.utc),
            allocated_capacity=10,
            status="published",
        )
        Event.objects.create(
            venue=self.venue,
            organizer=self.org,
            name="DraftEvent",
            date=datetime.now(timezone.utc),
            allocated_capacity=10,
            status="draft",
        )
        response = self.client.get(reverse("events:home"))
        self.assertContains(response, "PublicEvent")
        self.assertNotContains(response, "DraftEvent")

    def test_draft_event_detail_not_visible(self):
        draft = Event.objects.create(
            venue=self.venue,
            organizer=self.org,
            name="DraftEvent",
            date=datetime.now(timezone.utc),
            allocated_capacity=10,
            status="draft",
        )
        response = self.client.get(
            reverse("events:public_event_detail", args=[draft.pk])
        )
        self.assertEqual(response.status_code, 404)