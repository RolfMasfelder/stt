"""Custom DRF throttle classes for API rate limiting (ADR-14)."""

from rest_framework.throttling import UserRateThrottle


class UploadRateThrottle(UserRateThrottle):
    """Stricter rate limit for audio upload endpoints (10/min per user)."""

    scope = "upload"
