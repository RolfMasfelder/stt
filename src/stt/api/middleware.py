"""Middleware for security event audit logging (ADR-14) and multi-tenancy (FA-25)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import connection
from django.http import HttpResponse, JsonResponse

from .audit import log_audit
from .models import AuditAction, Tenant

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)


class TenantMiddleware:
    """Extract tenant from request and attach to ``request.tenant``.

    Tenant identification sources (in priority order):
    1. ``X-Tenant-ID`` header (UUID) — used by API gateways / SaaS proxy
    2. ``tenant_id`` claim in the OAuth2 access-token

    Requests without a tenant (e.g. health check, single-tenant mode) get
    ``request.tenant = None`` and pass through.  Endpoints that require a
    tenant must check explicitly.

    Sets ``app.current_tenant_id`` on the PostgreSQL session for RLS (2f.2).
    """

    # Paths that never need a tenant.
    _EXEMPT_PREFIXES = ("/health", "/o/", "/admin/", "/schema", "/docs")

    def __init__(self, get_response: callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.tenant = None  # type: ignore[attr-defined]

        # Skip tenant resolution for exempt paths.
        if any(request.path.startswith(p) for p in self._EXEMPT_PREFIXES):
            self._set_rls_tenant("")
            return self.get_response(request)

        tenant_id = self._resolve_tenant_id(request)
        if tenant_id:
            try:
                request.tenant = Tenant.objects.get(id=tenant_id, is_active=True)  # type: ignore[attr-defined]
            except (Tenant.DoesNotExist, ValueError):
                return JsonResponse(
                    {"detail": "Invalid or inactive tenant"},
                    status=403,
                )
            self._set_rls_tenant(str(request.tenant.id))
        else:
            self._set_rls_tenant("")

        return self.get_response(request)

    @staticmethod
    def _resolve_tenant_id(request: HttpRequest) -> str | None:
        """Return a tenant UUID string or None."""
        # 1. Explicit header (API gateway / proxy)
        header_val = request.META.get("HTTP_X_TENANT_ID")
        if header_val:
            return header_val.strip()

        # 2. OAuth2 access-token claim (django-oauth-toolkit stores the
        #    token on request after authentication).
        token = getattr(request, "auth", None)
        if token and hasattr(token, "tenant_id"):
            return str(token.tenant_id)

        return None

    @staticmethod
    def _set_rls_tenant(tenant_id: str) -> None:
        """Set the PostgreSQL session variable used by RLS policies."""
        with connection.cursor() as cursor:
            cursor.execute("SET app.current_tenant_id = %s", [tenant_id])


class AuditMiddleware:
    """Log security-relevant events: failed auth (401), rate limiting (429)."""

    def __init__(self, get_response: callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if response.status_code == 401:
            log_audit(
                AuditAction.AUTH_FAILED,
                request=request,
                detail=f"401 {request.method} {request.path}",
            )

        elif response.status_code == 429:
            log_audit(
                AuditAction.RATE_LIMITED,
                request=request,
                detail=f"429 {request.method} {request.path}",
            )

        return response
