"""Audit logging helper functions (FA-16, DSGVO Art. 30)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .models import AuditAction, AuditLog

if TYPE_CHECKING:
    from rest_framework.request import Request

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str | None:
    """Extract client IP from request, respecting X-Forwarded-For (Caddy)."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_actor(request: Request) -> str:
    """Extract actor identifier from request."""
    if hasattr(request, "user") and request.user and request.user.is_authenticated:
        return request.user.username or str(request.user.pk)
    return "anonymous"


def log_audit(
    action: AuditAction,
    *,
    request: Request | None = None,
    resource_type: str = "",
    resource_id: str = "",
    detail: str = "",
    actor: str = "",
    ip_address: str | None = None,
) -> AuditLog:
    """Create an audit log entry with actor and IP from request."""
    if request is not None:
        if not actor:
            actor = _get_actor(request)
        if ip_address is None:
            ip_address = _get_client_ip(request)

    entry = AuditLog.objects.create(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor=actor,
        ip_address=ip_address,
        detail=detail[:500],
    )
    logger.info(
        "AUDIT: %s by=%s resource=%s/%s",
        action,
        actor,
        resource_type,
        resource_id,
    )
    return entry
