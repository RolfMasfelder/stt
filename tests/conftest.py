"""Shared pytest configuration for STT tests."""

import os

import pytest

# Use local PostgreSQL container for tests.
os.environ.setdefault("DATABASE_URL", "postgres://stt:stt_dev@127.0.0.1:5432/stt")


@pytest.fixture(autouse=True)
def _disable_security_redirects(settings) -> None:
    """Disable TLS redirect in test environment (no reverse-proxy)."""
    settings.SECURE_SSL_REDIRECT = False
