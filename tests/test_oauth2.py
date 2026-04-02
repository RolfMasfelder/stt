"""Tests for OAuth2 authentication (ADR-07)."""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient

from stt.config import LLMConfig, MLServiceConfig


def _mock_config():
    mock_config = MagicMock()
    mock_config.log_level = "WARNING"
    mock_config.ml_service = MLServiceConfig()
    mock_config.llm = LLMConfig()
    return mock_config


@pytest.mark.django_db
class TestUnauthenticatedAccess:
    """Verify that protected endpoints reject unauthenticated requests."""

    def test_transcribe_requires_auth(self) -> None:
        client = APIClient()
        with patch("stt.api.views._get_config", return_value=_mock_config()):
            response = client.post("/v1/transcribe")
        assert response.status_code == 401

    def test_diarize_requires_auth(self) -> None:
        client = APIClient()
        with patch("stt.api.views._get_config", return_value=_mock_config()):
            response = client.post("/v1/diarize")
        assert response.status_code == 401

    def test_process_requires_auth(self) -> None:
        client = APIClient()
        with patch("stt.api.views._get_config", return_value=_mock_config()):
            response = client.post("/v1/process")
        assert response.status_code == 401

    def test_jobs_create_requires_auth(self) -> None:
        client = APIClient()
        with patch("stt.api.views._get_config", return_value=_mock_config()):
            response = client.post("/v1/jobs")
        assert response.status_code == 401

    def test_health_is_public(self) -> None:
        client = APIClient()
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.django_db
class TestInvalidToken:
    """Verify that invalid tokens are rejected."""

    def test_invalid_bearer_token_rejected(self) -> None:
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token-xyz")
        with patch("stt.api.views._get_config", return_value=_mock_config()):
            response = client.post("/v1/transcribe")
        assert response.status_code == 401

    def test_expired_token_rejected(self, test_user) -> None:
        from datetime import timedelta

        from django.utils import timezone
        from oauth2_provider.models import AccessToken, Application

        app = Application.objects.create(
            name="test-expired",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            user=test_user,
        )
        token = AccessToken.objects.create(
            user=test_user,
            token="expired-token-12345",
            application=app,
            expires=timezone.now() - timedelta(hours=1),
            scope="read write",
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.token}")
        with patch("stt.api.views._get_config", return_value=_mock_config()):
            response = client.post("/v1/transcribe")
        assert response.status_code == 401


@pytest.mark.django_db
class TestAuthenticatedAccess:
    """Verify that valid tokens grant access."""

    def test_valid_token_grants_access(self, auth_client) -> None:
        with patch("stt.api.views._get_config", return_value=_mock_config()):
            with patch("stt.api.views.transcribe_audio", return_value="text"):
                from io import BytesIO

                f = BytesIO(b"audio")
                f.name = "test.wav"
                response = auth_client.post(
                    "/v1/transcribe",
                    {"file": f},
                    format="multipart",
                )
        assert response.status_code == 200


@pytest.mark.django_db
class TestOAuth2ProviderSettings:
    """Verify OAuth2 provider configuration."""

    def test_pkce_required(self) -> None:
        from django.conf import settings

        assert settings.OAUTH2_PROVIDER["PKCE_REQUIRED"] is True

    def test_access_token_lifetime(self) -> None:
        from django.conf import settings

        assert settings.OAUTH2_PROVIDER["ACCESS_TOKEN_EXPIRE_SECONDS"] == 900

    def test_refresh_token_lifetime(self) -> None:
        from django.conf import settings

        assert settings.OAUTH2_PROVIDER["REFRESH_TOKEN_EXPIRE_SECONDS"] == 604800

    def test_token_rotation_enabled(self) -> None:
        from django.conf import settings

        assert settings.OAUTH2_PROVIDER["ROTATE_REFRESH_TOKEN"] is True

    def test_oauth2_urls_registered(self) -> None:
        from django.urls import reverse

        # DOT registers these standard endpoints
        assert reverse("oauth2_provider:token")
        assert reverse("oauth2_provider:authorize")
        assert reverse("oauth2_provider:revoke-token")

    def test_drf_uses_oauth2_authentication(self) -> None:
        from django.conf import settings

        auth_classes = settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]
        assert (
            "oauth2_provider.contrib.rest_framework.OAuth2Authentication"
            in auth_classes
        )

    def test_drf_requires_authentication_by_default(self) -> None:
        from django.conf import settings

        perm_classes = settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]
        assert "rest_framework.permissions.IsAuthenticated" in perm_classes

    def test_drf_enforces_scope_permissions(self) -> None:
        from django.conf import settings

        perm_classes = settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]
        assert (
            "oauth2_provider.contrib.rest_framework.TokenHasReadWriteScope"
            in perm_classes
        )

    def test_read_write_scopes_configured(self) -> None:
        from django.conf import settings

        assert settings.OAUTH2_PROVIDER["READ_SCOPE"] == "read"
        assert settings.OAUTH2_PROVIDER["WRITE_SCOPE"] == "write"


@pytest.mark.django_db
class TestScopePermissions:
    """Verify scope-based access control."""

    def test_read_only_token_cannot_post(self, test_user) -> None:
        """A token with only 'read' scope should be denied on POST endpoints."""
        from datetime import timedelta

        from django.utils import timezone
        from oauth2_provider.models import AccessToken, Application

        app = Application.objects.create(
            name="test-readonly",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            user=test_user,
        )
        token = AccessToken.objects.create(
            user=test_user,
            token="read-only-token-12345",
            application=app,
            expires=timezone.now() + timedelta(hours=1),
            scope="read",
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.token}")
        with patch("stt.api.views._get_config", return_value=_mock_config()):
            response = client.post("/v1/transcribe")
        assert response.status_code == 403

    def test_read_only_token_can_get_job(self, test_user) -> None:
        """A token with 'read' scope should be allowed on GET endpoints."""
        from datetime import timedelta

        from django.utils import timezone
        from oauth2_provider.models import AccessToken, Application

        from stt.api.models import Job, JobType

        app = Application.objects.create(
            name="test-readonly-get",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            user=test_user,
        )
        token = AccessToken.objects.create(
            user=test_user,
            token="read-only-get-token",
            application=app,
            expires=timezone.now() + timedelta(hours=1),
            scope="read",
        )
        job = Job.objects.create(job_type=JobType.TRANSCRIBE)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.token}")
        response = client.get(f"/v1/jobs/{job.id}")
        assert response.status_code == 200
