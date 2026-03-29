"""Django app configuration for the STT API."""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = "stt.api"
    label = "api"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "STT API"
