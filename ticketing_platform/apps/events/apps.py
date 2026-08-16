from django.apps import AppConfig


class EventsConfig(AppConfig):
    name = 'apps.events'

    def ready(self):
        from . import signals  # noqa: F401
