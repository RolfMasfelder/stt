"""Shared pytest configuration for STT tests."""

import os

import pytest
from django.contrib.auth import get_user_model
from oauth2_provider.models import AccessToken, Application
from rest_framework.test import APIClient

# Use local PostgreSQL container for tests.
os.environ.setdefault("DATABASE_URL", "postgres://stt:stt_dev@127.0.0.1:5432/stt")


@pytest.fixture(autouse=True)
def _disable_security_redirects(settings) -> None:
    """Disable TLS redirect in test environment (no reverse-proxy)."""
    settings.SECURE_SSL_REDIRECT = False


@pytest.fixture
def test_user(db):
    """Create a test user for authenticated API access."""
    User = get_user_model()
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def oauth2_token(test_user):
    """Create a valid OAuth2 access token for testing."""
    from datetime import timedelta

    from django.utils import timezone

    app = Application.objects.create(
        name="test-app",
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
        user=test_user,
    )
    token = AccessToken.objects.create(
        user=test_user,
        token="test-access-token-12345",
        application=app,
        expires=timezone.now() + timedelta(hours=1),
        scope="read write",
    )
    return token


@pytest.fixture
def auth_client(oauth2_token):
    """Create an authenticated DRF test client with OAuth2 token."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {oauth2_token.token}")
    return client
