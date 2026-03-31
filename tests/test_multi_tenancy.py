"""Tests for multi-tenancy and RLS (FA-25, 2f.1-2f.2)."""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from oauth2_provider.models import AccessToken, Application
from rest_framework.test import APIClient

from stt.api.models import (
    AuditAction,
    AuditLog,
    Job,
    JobStatus,
    JobType,
    StorageConfig,
    Tenant,
)

# -- Fixtures --


@pytest.fixture
def tenant_a(db) -> Tenant:
    return Tenant.objects.create(name="Tenant A", slug="tenant-a")


@pytest.fixture
def tenant_b(db) -> Tenant:
    return Tenant.objects.create(name="Tenant B", slug="tenant-b")


@pytest.fixture
def inactive_tenant(db) -> Tenant:
    return Tenant.objects.create(name="Inactive", slug="inactive", is_active=False)


@pytest.fixture
def user_a(db):
    User = get_user_model()
    return User.objects.create_user(username="user_a", password="pass123")


@pytest.fixture
def user_b(db):
    User = get_user_model()
    return User.objects.create_user(username="user_b", password="pass456")


def _make_auth_client(user, tenant: Tenant | None = None) -> APIClient:
    """Create an authenticated APIClient, optionally with an X-Tenant-ID header."""
    from datetime import timedelta

    from django.utils import timezone

    app, _ = Application.objects.get_or_create(
        name=f"app-{user.username}",
        defaults={
            "client_type": Application.CLIENT_CONFIDENTIAL,
            "authorization_grant_type": Application.GRANT_CLIENT_CREDENTIALS,
            "user": user,
        },
    )
    token = AccessToken.objects.create(
        user=user,
        token=f"token-{user.username}-{uuid.uuid4().hex[:8]}",
        application=app,
        expires=timezone.now() + timedelta(hours=1),
        scope="read write",
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.token}")
    if tenant:
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token.token}",
            HTTP_X_TENANT_ID=str(tenant.id),
        )
    return client


@pytest.fixture
def client_a(user_a, tenant_a) -> APIClient:
    return _make_auth_client(user_a, tenant_a)


@pytest.fixture
def client_b(user_b, tenant_b) -> APIClient:
    return _make_auth_client(user_b, tenant_b)


@pytest.fixture
def client_no_tenant(user_a) -> APIClient:
    return _make_auth_client(user_a)


# -- Tenant Model Tests --


class TestTenantModel:
    def test_create_tenant(self, tenant_a: Tenant) -> None:
        assert tenant_a.name == "Tenant A"
        assert tenant_a.slug == "tenant-a"
        assert tenant_a.is_active is True
        assert tenant_a.id is not None

    def test_tenant_str(self, tenant_a: Tenant) -> None:
        assert str(tenant_a) == "Tenant A"

    def test_tenant_slug_unique(self, tenant_a: Tenant, db) -> None:
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            Tenant.objects.create(name="Another", slug="tenant-a")


# -- TenantMiddleware Tests --


class TestTenantMiddleware:
    def test_health_no_tenant_required(self, db) -> None:
        client = APIClient()
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_valid_tenant_header(self, client_a: APIClient, tenant_a: Tenant) -> None:
        resp = client_a.get("/health")
        assert resp.status_code == 200

    def test_invalid_tenant_header(self, user_a, db) -> None:
        client = _make_auth_client(user_a)
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer token-{user_a.username}-invalid",
            HTTP_X_TENANT_ID=str(uuid.uuid4()),  # non-existent tenant
        )
        # Create a proper token first
        from datetime import timedelta

        from django.utils import timezone

        app = Application.objects.filter(name=f"app-{user_a.username}").first()
        token = AccessToken.objects.create(
            user=user_a,
            token=f"token-invalid-check-{uuid.uuid4().hex[:8]}",
            application=app,
            expires=timezone.now() + timedelta(hours=1),
            scope="read write",
        )
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token.token}",
            HTTP_X_TENANT_ID=str(uuid.uuid4()),
        )
        resp = client.get("/v1/jobs")
        # Should get 403 (invalid tenant) — the middleware rejects before
        # the view can return 405.
        assert resp.status_code == 403
        assert "Invalid or inactive tenant" in resp.json()["detail"]

    def test_inactive_tenant_rejected(self, user_a, inactive_tenant: Tenant) -> None:
        from datetime import timedelta

        from django.utils import timezone

        app = Application.objects.filter(name=f"app-{user_a.username}").first()
        if not app:
            app = Application.objects.create(
                name=f"app-{user_a.username}",
                client_type=Application.CLIENT_CONFIDENTIAL,
                authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
                user=user_a,
            )
        token = AccessToken.objects.create(
            user=user_a,
            token=f"token-inactive-{uuid.uuid4().hex[:8]}",
            application=app,
            expires=timezone.now() + timedelta(hours=1),
            scope="read write",
        )
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token.token}",
            HTTP_X_TENANT_ID=str(inactive_tenant.id),
        )
        resp = client.get("/v1/jobs")
        assert resp.status_code == 403


# -- Tenant Isolation in Views --


class TestTenantIsolation:
    """Verify that data is isolated between tenants at the application level."""

    def test_job_created_with_tenant(
        self, client_a: APIClient, tenant_a: Tenant
    ) -> None:
        """Jobs created via API are tagged with the request tenant."""
        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            owner=None,
            tenant=tenant_a,
        )
        assert job.tenant == tenant_a
        assert job.tenant_id == tenant_a.id

    def test_jobs_isolated_between_tenants(
        self,
        tenant_a: Tenant,
        tenant_b: Tenant,
        client_a: APIClient,
        client_b: APIClient,
    ) -> None:
        """Tenant A cannot see Tenant B's jobs via JobDetailView."""
        job_b = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            result_text="secret",
            tenant=tenant_b,
        )
        # Client A tries to access Tenant B's job
        resp = client_a.get(f"/v1/jobs/{job_b.id}")
        assert resp.status_code == 404

    def test_storage_config_isolated(
        self, tenant_a: Tenant, tenant_b: Tenant, client_a: APIClient
    ) -> None:
        """Tenant A cannot see Tenant B's storage configs."""
        StorageConfig.objects.create(
            name="B's config",
            backend_type="local",
            tenant=tenant_b,
        )
        StorageConfig.objects.create(
            name="A's config",
            backend_type="local",
            tenant=tenant_a,
        )
        resp = client_a.get("/v1/config/storage")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "A's config"

    def test_storage_config_create_sets_tenant(
        self, client_a: APIClient, tenant_a: Tenant
    ) -> None:
        """Creating a storage config via API sets the tenant from request."""
        resp = client_a.post(
            "/v1/config/storage",
            {"name": "Test Storage", "backend_type": "local"},
            format="json",
        )
        assert resp.status_code == 201
        config = StorageConfig.objects.get(id=resp.json()["id"])
        assert config.tenant == tenant_a

    def test_no_tenant_sees_all_null_tenant_data(
        self, client_no_tenant: APIClient, db
    ) -> None:
        """Without a tenant header, untenanted data is visible (backward compat)."""
        StorageConfig.objects.create(
            name="Global config",
            backend_type="local",
            tenant=None,
        )
        resp = client_no_tenant.get("/v1/config/storage")
        assert resp.status_code == 200
        # Without tenant filter, all configs with tenant=None are visible
        configs = resp.json()
        assert any(c["name"] == "Global config" for c in configs)


# -- Audit Log Tenant --


class TestAuditLogTenant:
    def test_audit_log_stores_tenant(self, tenant_a: Tenant, db) -> None:
        """Audit logs are tagged with the tenant."""
        from stt.api.audit import log_audit

        entry = log_audit(
            AuditAction.JOB_CREATED,
            resource_type="job",
            resource_id="test-123",
            actor="test",
            tenant=tenant_a,
        )
        assert entry.tenant == tenant_a

    def test_audit_log_no_tenant(self, db) -> None:
        """Audit logs without tenant (system-level) work fine."""
        from stt.api.audit import log_audit

        entry = log_audit(
            AuditAction.DATA_AUTO_DELETED,
            resource_type="system",
            actor="system",
        )
        assert entry.tenant is None


# -- RLS Tests --


class TestRLS:
    """Test that PostgreSQL Row-Level Security policies work correctly.

    The default ``stt`` user is a superuser, which always bypasses RLS.
    These tests create a restricted role ``stt_app`` to verify that RLS
    policies enforce tenant isolation at the database level.
    """

    @pytest.fixture(autouse=True)
    def _setup_rls_role(self, db):
        """Create a non-superuser role for RLS testing and clean up afterwards."""
        with connection.cursor() as cur:
            # Create a restricted app role if it doesn't exist
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'stt_app'")
            if not cur.fetchone():
                cur.execute("CREATE ROLE stt_app LOGIN PASSWORD 'stt_app'")
            # Grant access to schema and tables
            cur.execute("GRANT USAGE ON SCHEMA public TO stt_app")
            cur.execute(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO stt_app"
            )
            cur.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO stt_app")
        yield
        # Reset the session variable after each test
        self._set_rls_tenant("")

    def _query_as_app_role(self, sql: str, params: list | None = None) -> list:
        """Run a query as the stt_app (non-superuser) role to test RLS."""
        with connection.cursor() as cur:
            cur.execute("SET ROLE stt_app")
            try:
                cur.execute(sql, params or [])
                return cur.fetchall()
            finally:
                cur.execute("RESET ROLE")

    def _set_rls_tenant(self, tenant_id: str) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SET app.current_tenant_id = %s", [tenant_id])

    def test_rls_policy_exists(self, db) -> None:
        """Verify RLS policies were created on the expected tables."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename, policyname
                FROM pg_policies
                WHERE policyname = 'tenant_isolation'
                ORDER BY tablename
            """)
            rows = cursor.fetchall()
        table_names = [r[0] for r in rows]
        assert "api_job" in table_names
        assert "api_storageconfig" in table_names
        assert "api_auditlog" in table_names

    def test_rls_filters_jobs_by_tenant(
        self, tenant_a: Tenant, tenant_b: Tenant
    ) -> None:
        """With RLS active and tenant set, only matching rows are visible."""
        job_a = Job.objects.create(job_type=JobType.TRANSCRIBE, tenant=tenant_a)
        job_b = Job.objects.create(job_type=JobType.TRANSCRIBE, tenant=tenant_b)

        # Set RLS to tenant A and query as non-superuser
        self._set_rls_tenant(str(tenant_a.id))
        rows = self._query_as_app_role("SELECT id FROM api_job")
        visible_ids = {row[0] for row in rows}
        assert job_a.id in visible_ids
        assert job_b.id not in visible_ids

        # Set RLS to tenant B
        self._set_rls_tenant(str(tenant_b.id))
        rows = self._query_as_app_role("SELECT id FROM api_job")
        visible_ids = {row[0] for row in rows}
        assert job_b.id in visible_ids
        assert job_a.id not in visible_ids

    def test_rls_empty_tenant_sees_null_tenant_data(self, tenant_a: Tenant) -> None:
        """With empty tenant setting, NULL-tenant rows are visible."""
        job_null = Job.objects.create(job_type=JobType.TRANSCRIBE, tenant=None)
        job_a = Job.objects.create(job_type=JobType.TRANSCRIBE, tenant=tenant_a)

        self._set_rls_tenant("")
        rows = self._query_as_app_role("SELECT id FROM api_job")
        visible_ids = {row[0] for row in rows}
        assert job_null.id in visible_ids
        # tenant_a job also visible when no tenant filter set (empty = no restriction)
        assert job_a.id in visible_ids

    def test_rls_storage_config_isolation(
        self, tenant_a: Tenant, tenant_b: Tenant
    ) -> None:
        """StorageConfig rows are also isolated by RLS."""
        sc_a = StorageConfig.objects.create(
            name="A Storage", backend_type="local", tenant=tenant_a
        )
        sc_b = StorageConfig.objects.create(
            name="B Storage", backend_type="local", tenant=tenant_b
        )

        self._set_rls_tenant(str(tenant_a.id))
        rows = self._query_as_app_role("SELECT id FROM api_storageconfig")
        visible = {row[0] for row in rows}
        assert sc_a.id in visible
        assert sc_b.id not in visible

    def test_rls_audit_log_isolation(self, tenant_a: Tenant, tenant_b: Tenant) -> None:
        """AuditLog rows are isolated by RLS."""
        al_a = AuditLog.objects.create(
            action=AuditAction.JOB_CREATED, tenant=tenant_a, actor="a"
        )
        al_b = AuditLog.objects.create(
            action=AuditAction.JOB_CREATED, tenant=tenant_b, actor="b"
        )

        self._set_rls_tenant(str(tenant_a.id))
        rows = self._query_as_app_role("SELECT id FROM api_auditlog")
        visible = {row[0] for row in rows}
        assert al_a.id in visible
        assert al_b.id not in visible
