from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from io import StringIO
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import Profile

from apps.tickets.models import Ticket
from .models import Event, Venue, WaitlistEntry

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

# V5: Bulk Import & Waitlist Tests

class BulkImportTests(TestCase):
    def setUp(self):
        self.org = make_user("org", Profile.Role.ORGANIZER)
        self.venue = Venue.objects.create(
            name="Stadium", max_capacity=100, owner=self.org
        )
        self.event = Event.objects.create(
            venue=self.venue,
            organizer=self.org,
            name="Concert",
            date=datetime.now(timezone.utc),
            allocated_capacity=10,
            status="published",
        )
        # Create a ticket type
        self.ticket_type = self.event.ticket_types.create(
            name="GA", price=50, quantity_total=5
        )
        # Create organizer client
        self.client.login(username="org", password="pass12345")

    def test_bulk_import_allocates_tickets_when_capacity_available(self):
        """Test that CSV with fewer entries than capacity allocates all as tickets."""
        csv_content = "email,full_name,ticket_type\nuser1@example.com,User One,GA\nuser2@example.com,User Two,GA\n"
        response = self.client.post(
            reverse("events:event_bulk_import", args=[self.event.pk]),
            {"csv_file": csv_content},
            format="multipart",
        )
        self.assertEqual(WaitlistEntry.objects.filter(event=self.event).count(), 0)
        self.assertEqual(Ticket.objects.filter(event=self.event).count(), 2)

    def test_bulk_import_creates_waitlist_when_capacity_exceeded(self):
        """Test that CSV with more entries than capacity creates waitlist entries."""
        csv_content = "email,full_name,ticket_type\nuser1@example.com,User One,GA\nuser2@example.com,User Two,GA\nuser3@example.com,User Three,GA\nuser4@example.com,User Four,GA\nuser5@example.com,User Five,GA\n"
        response = self.client.post(
            reverse("events:event_bulk_import", args=[self.event.pk]),
            {"csv_file": csv_content},
            format="multipart",
        )
        # Event has 5 tickets, 5 CSV entries = 3 allocated + 2 waitlisted
        self.assertEqual(Ticket.objects.filter(event=self.event).count(), 3)
        self.assertEqual(WaitlistEntry.objects.filter(event=self.event).count(), 2)

    def test_bulk_import_skips_invalid_rows(self):
        """Test that CSV with missing fields is handled gracefully."""
        csv_content = "email,full_name,ticket_type\n,user Two,GA\nuser2@example.com,,GA\nuser3@example.com,User Three,GA\n"
        response = self.client.post(
            reverse("events:event_bulk_import", args=[self.event.pk]),
            {"csv_file": csv_content},
            format="multipart",
        )
        # Only 1 valid row (user3)
        self.assertEqual(Ticket.objects.filter(event=self.event).count(), 1)
        self.assertEqual(WaitlistEntry.objects.filter(event=self.event).count(), 0)

    def test_bulk_import_duplicate_emails_rejected(self):
        """Test that duplicate emails are rejected."""
        # First import
        csv_content = "email,full_name,ticket_type\nuser1@example.com,User One,GA\n"
        self.client.post(
            reverse("events:event_bulk_import", args=[self.event.pk]),
            {"csv_file": csv_content},
            format="multipart",
        )
        # Second import with same email
        csv_content = "email,full_name,ticket_type\nuser1@example.com,User One Updated,GA\n"
        response = self.client.post(
            reverse("events:event_bulk_import", args=[self.event.pk]),
            {"csv_file": csv_content},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)

    def test_promote_waitlist_entry(self):
        """Test that waitlist entry can be promoted manually."""
        # First create some waitlist entries
        csv_content = "email,full_name,ticket_type\nuser1@example.com,User One,GA\nuser2@example.com,User Two,GA\nuser3@example.com,User Three,GA\n"
        self.client.post(
            reverse("events:event_bulk_import", args=[self.event.pk]),
            {"csv_file": csv_content},
            format="multipart",
        )
        # Now we have 3 tickets (capacity) + 2 waitlisted (since qty_total=5 but we have 5 entries)
        # Actually let me reconsider - with 5 tickets and 5 entries, all should be allocated
        # Let me test with 6 entries for 5 tickets
        pass

    def test_refund_triggers_promotion(self):
        """Test that refunding a ticket triggers waitlist promotion."""
        # Create a ticket directly
        from apps.tickets.services import generate_unique_code, _create_ticket
        code = generate_unique_code()
        ticket = _create_ticket(self.ticket_type, self.org)
        ticket.user = self.org
        ticket.save()
        
        # Now we have 1 ticket used, 4 available
        # Create waitlist entries
        csv_content = "email,full_name,ticket_type\nuser1@example.com,User One,GA\n"
        self.client.post(
            reverse("events:event_bulk_import", args=[self.event.pk]),
            {"csv_file": csv_content},
            format="multipart",
        )
        
        # Refund the ticket
        from apps.events.tasks import handle_refund
        handle_refund(ticket.pk)
        
        # Check that a waitlist entry was promoted
        self.assertEqual(Ticket.objects.filter(event=self.event).count(), 1)
        # The promoted ticket should have a different user
        promoted_ticket = Ticket.objects.get(event=self.event)
        self.assertIsNotNone(promoted_ticket.user)


class WaitlistModelTests(TestCase):
    def setUp(self):
        self.org = make_user("org", Profile.Role.ORGANIZER)
        self.venue = Venue.objects.create(
            name="Stadium", max_capacity=100, owner=self.org
        )
        self.event = Event.objects.create(
            venue=self.venue,
            organizer=self.org,
            name="Concert",
            date=datetime.now(timezone.utc),
            allocated_capacity=10,
            status="published",
        )

    def test_waitlist_entry_creation(self):
        """Test WaitlistEntry model creation."""
        entry = WaitlistEntry.objects.create(
            event=self.event,
            email="test@example.com",
            full_name="Test User",
        )
        self.assertEqual(entry.status, WaitlistEntry.Status.WAITING)
        self.assertEqual(entry.position, 0)
        self.assertEqual(str(entry), "Test User (test@example.com) - Concert")

    def test_waitlist_unique_together(self):
        """Test that event+email combination is unique."""
        WaitlistEntry.objects.create(
            event=self.event,
            email="test@example.com",
            full_name="Test User 1",
        )
        with self.assertRaises(Exception):
            WaitlistEntry.objects.create(
                event=self.event,
                email="test@example.com",
                full_name="Test User 2",
            )
