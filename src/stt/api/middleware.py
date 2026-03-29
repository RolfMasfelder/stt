"""Middleware for security event audit logging (ADR-14)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.http import HttpResponse

from .audit import log_audit
from .models import AuditAction

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)


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
