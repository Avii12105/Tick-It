from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db.utils import OperationalError
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Profile
from apps.events.models import Event, Venue

from .models import Reservation, TicketType
from .services import RESERVATION_LOCK_MINUTES, reserve_tickets

User = get_user_model()


def make_user(username, role=Profile.Role.ATTENDEE):
    user = User.objects.create_user(username=username, password="pass12345")
    user.profile.role = role
    user.profile.save()
    return user


def make_event(allocated=100, status="published"):
    org = make_user(f"org_{Event.objects.count()}", Profile.Role.ORGANIZER)
    venue = Venue.objects.create(
        name="Stadium", max_capacity=allocated, owner=org
    )
    return Event.objects.create(
        venue=venue,
        organizer=org,
        name="Concert",
        date=timezone.now() + timedelta(days=7),
        allocated_capacity=allocated,
        status=status,
    )


class TicketTypeCapacityTests(TestCase):
    def setUp(self):
        self.event = make_event(allocated=100)

    def test_clean_rejects_tiers_exceeding_event_capacity(self):
        TicketType.objects.create(
            event=self.event, name="GA", price=50, quantity_total=70
        )
        tier = TicketType(
            event=self.event, name="VIP", price=200, quantity_total=40
        )
        with self.assertRaises(ValidationError):
            tier.full_clean()

    def test_signal_rejects_direct_save_exceeding(self):
        TicketType.objects.create(
            event=self.event, name="GA", price=50, quantity_total=70
        )
        with self.assertRaises(ValidationError):
            TicketType.objects.create(
                event=self.event, name="VIP", price=200, quantity_total=40
            )

    def test_within_capacity_allowed(self):
        TicketType.objects.create(
            event=self.event, name="GA", price=50, quantity_total=70
        )
        TicketType.objects.create(
            event=self.event, name="VIP", price=200, quantity_total=30
        )
        self.assertEqual(TicketType.allocated_total(self.event), 100)

    def test_quantity_total_cannot_be_less_than_sold(self):
        tier = TicketType.objects.create(
            event=self.event, name="GA", price=50, quantity_total=100
        )
        TicketType.objects.filter(pk=tier.pk).update(quantity_sold=40)
        tier.refresh_from_db()
        tier.quantity_total = 30
        with self.assertRaises(ValidationError):
            tier.full_clean()
        with self.assertRaises(ValidationError):
            tier.save()


class ReservationLogicTests(TestCase):
    def setUp(self):
        self.event = make_event(allocated=100)
        self.tier = TicketType.objects.create(
            event=self.event, name="GA", price=50, quantity_total=10
        )
        self.user = make_user("bob")

    def test_reserve_creates_active_reservation(self):
        reservation = reserve_tickets(self.tier.pk, self.user, 2)
        self.assertEqual(reservation.status, Reservation.Status.ACTIVE)
        expected_expiry = timezone.now() + timedelta(
            minutes=RESERVATION_LOCK_MINUTES
        )
        self.assertAlmostEqual(
            reservation.expires_at, expected_expiry, delta=timedelta(seconds=5)
        )

    def test_available_count_decreases_with_reservations(self):
        reserve_tickets(self.tier.pk, self.user, 3)
        reserve_tickets(self.tier.pk, make_user("carol"), 2)
        self.assertEqual(self.tier.available_count(), 5)

    def test_expired_reservations_do_not_reduce_availability(self):
        reservation = reserve_tickets(self.tier.pk, self.user, 4)
        Reservation.objects.filter(pk=reservation.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertEqual(self.tier.available_count(), 10)

    def test_cannot_reserve_more_than_available(self):
        reserve_tickets(self.tier.pk, self.user, 9)
        with self.assertRaises(ValidationError):
            reserve_tickets(self.tier.pk, make_user("carol"), 2)

    def test_remove_releases_inventory(self):
        reservation = reserve_tickets(self.tier.pk, self.user, 4)
        reservation.delete()
        self.assertEqual(self.tier.available_count(), 10)


class CartFlowTests(TestCase):
    def setUp(self):
        self.event = make_event(allocated=100, status="published")
        self.tier = TicketType.objects.create(
            event=self.event, name="GA", price=50, quantity_total=10
        )
        self.user = make_user("bob")

    def test_anonymous_add_to_cart_redirects_to_login(self):
        response = self.client.post(
            reverse("tickets:add_to_cart"),
            {"ticket_type": self.tier.pk, "quantity": 1},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)
        self.assertIn("next", response.url)

    def test_authenticated_add_to_cart_creates_reservation(self):
        self.client.login(username="bob", password="pass12345")
        response = self.client.post(
            reverse("tickets:add_to_cart"),
            {"ticket_type": self.tier.pk, "quantity": 2},
        )
        self.assertRedirects(
            response,
            reverse("events:public_event_detail", args=[self.event.pk]),
        )
        self.assertTrue(
            Reservation.objects.filter(
                user=self.user, ticket_type=self.tier, quantity=2
            ).exists()
        )

    def test_cart_shows_only_active_reservations(self):
        self.client.login(username="bob", password="pass12345")
        active = reserve_tickets(self.tier.pk, self.user, 1)
        stale = reserve_tickets(self.tier.pk, self.user, 1)
        Reservation.objects.filter(pk=stale.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        response = self.client.get(reverse("tickets:cart"))
        self.assertContains(response, active.ticket_type.name)
        self.assertNotContains(response, "Removed")

    def test_remove_from_cart_deletes_reservation(self):
        self.client.login(username="bob", password="pass12345")
        reservation = reserve_tickets(self.tier.pk, self.user, 3)
        self.client.post(
            reverse("tickets:remove_from_cart", args=[reservation.pk])
        )
        self.assertFalse(
            Reservation.objects.filter(pk=reservation.pk).exists()
        )
        self.assertEqual(self.tier.available_count(), 10)

    def test_event_detail_shows_ticket_tiers(self):
        response = self.client.get(
            reverse("events:public_event_detail", args=[self.event.pk])
        )
        self.assertContains(response, "GA")
        self.assertContains(response, "Add to cart")

    def test_tier_over_capacity_form_rejected(self):
        TicketType.objects.create(
            event=self.event, name="GA", price=50, quantity_total=70
        )
        org = self.event.organizer
        self.client.login(username=org.username, password="pass12345")
        response = self.client.post(
            reverse("tickets:ticket_type_create", args=[self.event.pk]),
            {"name": "VIP", "price": "200.00", "quantity_total": 40},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("quantity_total", form.errors)
        self.assertFalse(TicketType.objects.filter(name="VIP").exists())

    def test_organizer_tier_crud_gated(self):
        attendee = make_user("eve")
        self.client.login(username="eve", password="pass12345")
        response = self.client.get(
            reverse("tickets:ticket_type_create", args=[self.event.pk])
        )
        self.assertRedirects(response, reverse("events:home"))
        self.client.logout()
        org = self.event.organizer
        self.client.login(username=org.username, password="pass12345")
        response = self.client.post(
            reverse("tickets:ticket_type_create", args=[self.event.pk]),
            {"name": "VIP", "price": "200.00", "quantity_total": 10},
        )
        self.assertRedirects(
            response,
            reverse("events:organizer_event_detail", args=[self.event.pk]),
        )
        self.assertTrue(
            TicketType.objects.filter(event=self.event, name="VIP").exists()
        )


class ExpireCommandTests(TestCase):
    def test_command_expires_stale_reservations(self):
        event = make_event(allocated=100)
        tier = TicketType.objects.create(
            event=event, name="GA", price=50, quantity_total=10
        )
        user = make_user("bob")
        stale = reserve_tickets(tier.pk, user, 2)
        Reservation.objects.filter(pk=stale.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        fresh = reserve_tickets(tier.pk, user, 1)
        call_command("expire_reservations")
        stale.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual(stale.status, Reservation.Status.EXPIRED)
        self.assertEqual(fresh.status, Reservation.Status.ACTIVE)


class ReservationConcurrencyTests(TransactionTestCase):
    def test_parallel_reserves_do_not_oversell(self):
        event = make_event(allocated=10)
        tier = TicketType.objects.create(
            event=event, name="GA", price=50, quantity_total=1
        )
        users = [make_user(f"racer{i}") for i in range(4)]

        def attempt(user):
            from django.db import connection

            try:
                reserve_tickets(tier.pk, user, 1)
                return True
            except (ValidationError, OperationalError):
                return False
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(attempt, users))

        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 3)
        self.assertEqual(tier.reserved_count(), 1)