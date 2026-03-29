"""Tests for audit logging: helper, middleware, and actor/IP population."""

from unittest.mock import patch

import pytest
from django.test import RequestFactory
from rest_framework.test import APIClient

from stt.api.audit import _get_actor, _get_client_ip, log_audit
from stt.api.models import AuditAction, AuditLog


@pytest.fixture
def rf() -> RequestFactory:
    return RequestFactory()


# --- Unit tests for helper functions ---


class TestGetClientIp:
    def test_from_x_forwarded_for(self, rf) -> None:
        request = rf.get("/", HTTP_X_FORWARDED_FOR="1.2.3.4, 10.0.0.1")
        assert _get_client_ip(request) == "1.2.3.4"

    def test_from_remote_addr(self, rf) -> None:
        request = rf.get("/")
        assert _get_client_ip(request) == "127.0.0.1"


class TestGetActor:
    def test_authenticated_user(self, rf, test_user) -> None:
        request = rf.get("/")
        request.user = test_user
        assert _get_actor(request) == "testuser"

    def test_anonymous_user(self, rf) -> None:
        from django.contrib.auth.models import AnonymousUser

        request = rf.get("/")
        request.user = AnonymousUser()
        assert _get_actor(request) == "anonymous"

    def test_no_user_attribute(self, rf) -> None:
        request = rf.get("/")
        # RequestFactory doesn't always set user
        if hasattr(request, "user"):
            delattr(request, "user")
        assert _get_actor(request) == "anonymous"


class TestLogAudit:
    def test_creates_entry_with_request(self, rf, test_user) -> None:
        request = rf.get("/", HTTP_X_FORWARDED_FOR="10.20.30.40")
        request.user = test_user
        entry = log_audit(
            AuditAction.JOB_CREATED,
            request=request,
            resource_type="job",
            resource_id="abc-123",
        )
        assert entry.action == AuditAction.JOB_CREATED
        assert entry.actor == "testuser"
        assert entry.ip_address == "10.20.30.40"
        assert entry.resource_type == "job"
        assert entry.resource_id == "abc-123"

    def test_creates_entry_without_request(self, db) -> None:
        entry = log_audit(
            AuditAction.JOB_COMPLETED,
            resource_type="job",
            resource_id="xyz",
            actor="system",
        )
        assert entry.actor == "system"
        assert entry.ip_address is None

    def test_detail_truncated_to_500(self, db) -> None:
        long_detail = "x" * 600
        entry = log_audit(
            AuditAction.JOB_FAILED,
            detail=long_detail,
        )
        assert len(entry.detail) == 500

    def test_explicit_actor_overrides_request(self, rf, test_user) -> None:
        request = rf.get("/")
        request.user = test_user
        entry = log_audit(
            AuditAction.JOB_CREATED,
            request=request,
            actor="override-actor",
        )
        assert entry.actor == "override-actor"


# --- Middleware integration tests ---


class TestAuditMiddleware:
    def test_auth_failure_logged(self, db) -> None:
        """Unauthenticated request → 401 → AuditLog with AUTH_FAILED."""
        client = APIClient()  # no credentials
        response = client.get("/v1/jobs/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 401

        entry = AuditLog.objects.filter(action=AuditAction.AUTH_FAILED).first()
        assert entry is not None
        assert "401" in entry.detail
        assert entry.actor == "anonymous"

    def test_rate_limit_logged(self, auth_client, db) -> None:
        """Throttled request → 429 → AuditLog with RATE_LIMITED."""
        with patch(
            "stt.api.throttles.UploadRateThrottle.get_rate",
            return_value="0/minute",
        ):
            from django.core.cache import cache

            cache.clear()
            from io import BytesIO

            audio = BytesIO(b"\x00" * 100)
            audio.name = "test.wav"
            response = auth_client.post(
                "/v1/jobs",
                {"file": audio, "job_type": "transcribe"},
                format="multipart",
            )
            assert response.status_code == 429

        entry = AuditLog.objects.filter(action=AuditAction.RATE_LIMITED).first()
        assert entry is not None
        assert "429" in entry.detail
        assert entry.actor == "testuser"

    def test_successful_request_not_logged_as_security_event(
        self, auth_client, db
    ) -> None:
        """Normal 200 request should not create AUTH_FAILED or RATE_LIMITED."""
        auth_client.get("/health")
        security_events = AuditLog.objects.filter(
            action__in=[AuditAction.AUTH_FAILED, AuditAction.RATE_LIMITED],
        )
        assert security_events.count() == 0


class TestJobCreateAuditPopulatesActor:
    """Verify that job creation now populates actor and ip_address."""

    @patch("stt.api.views.async_task")
    def test_job_audit_has_actor_and_ip(self, mock_async, auth_client) -> None:
        from io import BytesIO

        audio = BytesIO(b"\x00" * 100)
        audio.name = "test.wav"
        response = auth_client.post(
            "/v1/jobs",
            {"file": audio, "job_type": "transcribe"},
            format="multipart",
        )
        assert response.status_code == 202
        job_id = response.json()["id"]

        entry = AuditLog.objects.get(
            action=AuditAction.JOB_CREATED,
            resource_id=job_id,
        )
        assert entry.actor == "testuser"
        # Test client uses REMOTE_ADDR default
        assert entry.ip_address is not None
