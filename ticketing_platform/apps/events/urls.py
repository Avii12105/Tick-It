from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.home, name="home"),
    path("events/", views.home, name="public_event_list"),
    path("events/<int:pk>/", views.event_detail, name="public_event_detail"),
    path(
        "organizer/venues/",
        views.venue_list,
        name="venue_list",
    ),
    path(
        "organizer/venues/new/",
        views.venue_create,
        name="venue_create",
    ),
    path(
        "organizer/venues/<int:pk>/",
        views.venue_detail,
        name="venue_detail",
    ),
    path(
        "organizer/venues/<int:pk>/edit/",
        views.venue_update,
        name="venue_update",
    ),
    path(
        "organizer/venues/<int:pk>/delete/",
        views.venue_delete,
        name="venue_delete",
    ),
    path(
        "organizer/events/",
        views.organizer_event_list,
        name="organizer_event_list",
    ),
    path(
        "organizer/events/new/",
        views.event_create,
        name="event_create",
    ),
    path(
        "organizer/events/<int:pk>/edit/",
        views.event_update,
        name="event_update",
    ),
    path(
        "organizer/events/<int:pk>/delete/",
        views.event_delete,
        name="event_delete",
    ),
]