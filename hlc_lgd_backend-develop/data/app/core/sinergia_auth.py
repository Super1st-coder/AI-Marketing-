"""Sinergia service-account authentication.

Fury talks to Sinergia using a static service API key transmitted via the
`X-Service-API-Key` header. Sinergia validates the key server-side.

Usage:
    token = await sinergia_auth.get_token()
    headers = {"X-Service-API-Key": token}
"""
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class SinergiaAuthClient:
    """Provides the service API key for Fury → Sinergia requests.

    Kept as a class for interface compatibility with campaign_tools.py.
    No JWT login, no token caching — just returns the static key from config.
    """

    async def get_token(self) -> str:
        """Return the service API key."""
        key = settings.SINERGIA_SERVICE_API_KEY
        if not key:
            raise RuntimeError(
                "SINERGIA_SERVICE_API_KEY must be set in Fury's environment."
            )
        return key

    def invalidate(self) -> None:
        """No-op: static key never needs invalidation."""
        pass


sinergia_auth = SinergiaAuthClient()
