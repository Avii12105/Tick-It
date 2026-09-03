from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path("cart/", views.cart, name="cart"),
    path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:pk>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/checkout/", views.checkout, name="checkout"),
    path("my-tickets/", views.my_tickets, name="my_tickets"),
    path("my-tickets/status/", views.my_tickets_status, name="my_tickets_status"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:pk>/status/", views.ticket_status, name="ticket_status"),
    path(
        "organizer/events/<int:event_pk>/tickets/new/",
        views.ticket_type_create,
        name="ticket_type_create",
    ),
    path(
        "tickets/<int:pk>/edit/",
        views.ticket_type_update,
        name="ticket_type_update",
    ),
    path(
        "tickets/<int:pk>/delete/",
        views.ticket_type_delete,
        name="ticket_type_delete",
    ),
]