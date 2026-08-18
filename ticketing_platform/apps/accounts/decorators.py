from functools import wraps
from urllib.parse import quote

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


def organizer_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            next_url = quote(request.get_full_path())
            return redirect(f"{reverse('accounts:login')}?next={next_url}")
        if not request.user.profile.is_organizer():
            messages.error(request, "You need an Organizer account to do that.")
            return redirect("events:home")
        return view_func(request, *args, **kwargs)

    return wrapper