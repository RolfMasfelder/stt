"""WSGI config for the STT project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stt.settings")

application = get_wsgi_application()
