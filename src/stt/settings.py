"""Django settings for the STT project."""

from pathlib import Path

import environ

env = environ.Env()

# Build paths: src/stt/settings.py -> project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Read .env file if present
env.read_env(BASE_DIR / ".env", overwrite=False)

# --- Security ---

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-in-production")

DEBUG = env.bool("DEBUG", default=False)

# Restrict in production via ALLOWED_HOSTS env variable (comma-separated).
ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=["*"])

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

DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgres://stt:stt_dev@127.0.0.1:5432/stt"
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

CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)

# --- File upload limits (2 GB) ---

DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024 * 1024

# --- django-q2 Task Queue ---

Q_CLUSTER = {
    "name": "stt",
    "workers": int(env("Q_WORKERS", default="2")),
    "timeout": int(env("Q_TIMEOUT", default="1800")),  # 30 min per task
    "retry": int(env("Q_RETRY", default="2100")),  # retry after 35 min
    "queue_limit": int(env("Q_QUEUE_LIMIT", default="50")),
    "orm": "default",  # Use PostgreSQL as broker
    "catch_up": False,  # Don't process missed schedules
}
