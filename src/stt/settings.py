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

# Storage encryption key (ADR-08) — 32-byte hex-encoded AES-256 key.
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
STORAGE_ENCRYPTION_KEY: str = os.getenv("STORAGE_ENCRYPTION_KEY", "")

# Restrict in production via ALLOWED_HOSTS env variable (comma-separated).
_hosts = os.getenv("ALLOWED_HOSTS", "*")
ALLOWED_HOSTS: list[str] = [h.strip() for h in _hosts.split(",") if h.strip()]

# --- Application definition ---

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "oauth2_provider",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "django_q",
    "stt.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "stt.api.middleware.TenantMiddleware",
    "stt.api.middleware.AuditMiddleware",
]

ROOT_URLCONF = "stt.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

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

# --- Static files ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Django REST Framework ---

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "oauth2_provider.contrib.rest_framework.TokenHasReadWriteScope",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "60/minute",
        "upload": "10/minute",  # For audio upload endpoints (ADR-14)
    },
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
    "OAUTH2_FLOWS": ["clientCredentials", "authorizationCode"],
    "OAUTH2_TOKEN_URL": "/o/token/",
    "OAUTH2_AUTHORIZATION_URL": "/o/authorize/",
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

# --- GDPR / Data Retention (ADR-13, 2e.2) ---

# Number of days to retain completed/failed jobs before auto-deletion.
# Set to 0 to disable auto-deletion.
DATA_RETENTION_DAYS: int = int(os.getenv("DATA_RETENTION_DAYS", "90"))

# --- django-q2 Task Queue ---

Q_CLUSTER = {
    "name": "stt",
    "workers": int(os.getenv("Q_WORKERS", "2")),
    "timeout": int(os.getenv("Q_TIMEOUT", "1800")),  # 30 min per task
    "retry": int(os.getenv("Q_RETRY", "2100")),  # retry after 35 min
    "queue_limit": int(os.getenv("Q_QUEUE_LIMIT", "50")),
    "orm": "default",  # Use PostgreSQL as broker
    "catch_up": False,  # Don't process missed schedules
    "schedules": [
        {
            "func": "stt.api.tasks.auto_delete_expired_jobs",
            "schedule_type": "D",  # Daily
            "name": "gdpr-auto-delete",
        },
    ],
}

# --- Reverse-Proxy / TLS Security (ADR-08, ADR-14) ---

# Trust X-Forwarded-Proto from Caddy reverse-proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Use forwarded host header from Caddy
USE_X_FORWARDED_HOST = True

# Security settings when behind reverse-proxy (non-DEBUG only)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^health$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 63072000  # 2 years
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# --- OAuth2 Provider (django-oauth-toolkit, ADR-07) ---

OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": 900,  # 15 minutes
    "REFRESH_TOKEN_EXPIRE_SECONDS": 604800,  # 7 days
    "ROTATE_REFRESH_TOKEN": True,
    "ALLOWED_REDIRECT_URI_SCHEMES": [
        "https",
        "http",
        "stt.app",
    ],  # stt.app for mobile PKCE
    "PKCE_REQUIRED": True,  # Enforce PKCE for all public clients (ADR-07)
    "SCOPES": {
        "read": "Read access to API resources",
        "write": "Write access (upload, process)",
    },
    "DEFAULT_SCOPES": ["read", "write"],
    "READ_SCOPE": "read",  # Used by TokenHasReadWriteScope for GET
    "WRITE_SCOPE": "write",  # Used by TokenHasReadWriteScope for POST
    "OAUTH2_BACKEND_CLASS": "oauth2_provider.oauth2_backends.OAuthLibCore",
}
