from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from django.middleware.csrf import get_token
from django.contrib import messages as django_messages
from jinja2 import Environment


def csrf_token():
    return get_token


def url(viewname, *args, **kwargs):
    return reverse(viewname, args=args, kwargs=kwargs)


def environment(**options):
    env = Environment(**options)
    env.globals.update(
        {
            "url": url,
            "static": staticfiles_storage.url,
        }
    )
    return env
