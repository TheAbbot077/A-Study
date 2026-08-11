import os

from django.core.exceptions import ImproperlyConfigured

from .base import *

_production_secret_key = os.getenv("DJANGO_SECRET_KEY", "").strip()
if not _production_secret_key or _production_secret_key in {
    "unsafe-local-dev-key",
    "replace-me-later",
    "django-insecure-93%8mdh-uhalbv7y3*@xy#v)$r7yt%0o(u&tay=j$l%$vpt^tr",
}:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set to a non-default production value.")

SECRET_KEY = _production_secret_key
DEBUG = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
