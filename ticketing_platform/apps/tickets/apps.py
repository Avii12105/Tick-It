from django.apps import AppConfig


class TicketsConfig(AppConfig):
    name = 'apps.tickets'

    def ready(self):
        from . import signals  # noqa: F401
