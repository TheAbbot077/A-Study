from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "backend"]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
