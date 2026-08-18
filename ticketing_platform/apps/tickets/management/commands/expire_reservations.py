from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tickets.models import Reservation


class Command(BaseCommand):
    help = "Expire stale active reservations and release their inventory."

    def handle(self, *args, **options):
        now = timezone.now()
        expired = Reservation.objects.filter(
            status=Reservation.Status.ACTIVE,
            expires_at__lte=now,
        ).update(status=Reservation.Status.EXPIRED)
        self.stdout.write(
            self.style.SUCCESS(f"Expired {expired} reservation(s).")
        )