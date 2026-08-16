from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from jinja2 import Environment


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