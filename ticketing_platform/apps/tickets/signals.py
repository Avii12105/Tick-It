from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import TicketType, validate_ticket_type_capacity


@receiver(pre_save, sender=TicketType)
def enforce_ticket_type_capacity(sender, instance, **kwargs):
    validate_ticket_type_capacity(instance)