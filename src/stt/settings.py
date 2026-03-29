"""Django settings for the STT project."""

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

# Build paths: src/stt/settings.py -> project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Read .env file if present (same mechanism as config.py / load_config)
load_dotenv(BASE_DIR / ".env")

# --- Security ---

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-dev-key-change-in-production")

DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# Restrict in production via ALLOWED_HOSTS env variable (comma-separated).
_hosts = os.getenv("ALLOWED_HOSTS", "*")
ALLOWED_HOSTS: list[str] = [h.strip() for h in _hosts.split(",") if h.strip()]

# --- Application definition ---

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "django_q",
    "stt.api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "stt.urls"

WSGI_APPLICATION = "stt.wsgi.application"

# --- Database ---


def _parse_database_url(url: str) -> dict:
    """Parse a DATABASE_URL into Django DATABASES dict entry."""
    parsed = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "127.0.0.1",
        "PORT": str(parsed.port or 5432),
    }


DATABASES = {
    "default": _parse_database_url(
        os.getenv("DATABASE_URL", "postgres://stt:stt_dev@127.0.0.1:5432/stt")
    ),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework ---

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "STT Server API",
    "DESCRIPTION": (
        "Speech-to-Text Server mit Transkription, Sprechererkennung und Zusammenfassung"
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- CORS ---

CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "true").lower() in (
    "true",
    "1",
    "yes",
)

# --- File upload limits (2 GB) ---

DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024 * 1024

# --- django-q2 Task Queue ---

Q_CLUSTER = {
    "name": "stt",
    "workers": int(os.getenv("Q_WORKERS", "2")),
    "timeout": int(os.getenv("Q_TIMEOUT", "1800")),  # 30 min per task
    "retry": int(os.getenv("Q_RETRY", "2100")),  # retry after 35 min
    "queue_limit": int(os.getenv("Q_QUEUE_LIMIT", "50")),
    "orm": "default",  # Use PostgreSQL as broker
    "catch_up": False,  # Don't process missed schedules
}
