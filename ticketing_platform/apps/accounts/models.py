from django.conf import settings
from django.db import models


class Profile(models.Model):
    class Role(models.TextChoices):
        ORGANIZER = "organizer", "Organizer"
        ATTENDEE = "attendee", "Attendee"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ATTENDEE,
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    def is_organizer(self):
        return self.role == self.Role.ORGANIZER