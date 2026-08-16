from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Event, Venue, validate_venue_capacity


@receiver(pre_save, sender=Event)
def enforce_capacity_on_save(sender, instance, **kwargs):
    if instance.allocated_capacity and instance.venue_id:
        venue = instance.venue
        if instance.allocated_capacity > venue.max_capacity:
            raise ValidationError(
                {
                    "allocated_capacity": (
                        f"Cannot exceed venue capacity of {venue.max_capacity}."
                    )
                }
            )


@receiver(pre_save, sender=Venue)
def enforce_capacity_against_existing_events(sender, instance, **kwargs):
    validate_venue_capacity(instance)