"""
Authentication & authorization utilities for the Fury API.

Three authentication mechanisms are supported, chosen per-route:

1. **OIDC** (``verify_oidc_token``)
   Used by the /agent-tools/* endpoints that are called by Google Cloud
   Vertex AI Agent Engine.  The engine attaches a Google-signed OIDC identity
   token as a Bearer token.  We verify the signature with google-auth and
   validate the ``aud`` claim matches ``settings.OIDC_AUDIENCE``.

2. **Internal API key** (``verify_internal_api_key``)
   Used by the /variants, /jobs, and /ad/* endpoints that are called by
   Sinergia (our own backend).  Sinergia must send:
       ``X-Internal-API-Key: <FURY_INTERNAL_API_KEY>``
   The key is shared via Secret Manager and configured via the env var
   ``FURY_INTERNAL_API_KEY``.

3. **Webhook secret** (already validated inline in webhooks.py via path param)
   Not re-implemented here; the existing secret-in-path approach is kept.

Environment variables required:
    FURY_INTERNAL_API_KEY   — shared secret for Sinergia → Fury calls
    OIDC_AUDIENCE           — expected ``aud`` in Agent Engine OIDC tokens
                              (usually the Cloud Run / GKE service URL)
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Security scheme objects (used by FastAPI's OpenAPI UI / Swagger)
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=True)
_api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=True)

# ---------------------------------------------------------------------------
# Mechanism 1 — Google OIDC (Agent Engine)
# ---------------------------------------------------------------------------

_GOOGLE_CERT_URL = "https://www.googleapis.com/oauth2/v3/certs"


@lru_cache(maxsize=1)
def _get_google_certs() -> dict[str, Any]:
    """Fetch Google's public JWK certs (cached until process restart).

    In production these rotate roughly every 6 hours; the cache is acceptable
    because the process restarts regularly on container deploys.  For longer
    uptime, replace the lru_cache with a TTL-aware cache.
    """
    try:
        resp = httpx.get(_GOOGLE_CERT_URL, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error(f"Failed to fetch Google JWK certs: {exc}")
        raise


def verify_oidc_token(
    credentials: HTTPAuthorizationCredentials = Security(_bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency — verify Google Cloud OIDC Bearer token.

    Raises HTTP 401 if the token is missing, invalid, expired, or the audience
    does not match ``settings.OIDC_AUDIENCE``.

    Returns the decoded token claims on success.
    """
    token = credentials.credentials

    if not settings.OIDC_AUDIENCE:
        # Guard against misconfiguration — fail securely rather than silently
        logger.error("OIDC_AUDIENCE is not configured; rejecting all OIDC requests")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC authentication is not configured on this server",
        )

    try:
        # google-auth validates signature, expiry, and audience in one call.
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        claims = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=settings.OIDC_AUDIENCE,
        )
        logger.debug(f"OIDC token verified for subject={claims.get('sub')}")
        return claims

    except Exception as exc:
        logger.warning(f"OIDC token verification failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google OIDC token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Mechanism 2 — Internal API key (Sinergia → Fury)
# ---------------------------------------------------------------------------


def verify_internal_api_key(
    provided_key: str = Security(_api_key_header),
) -> str:
    """FastAPI dependency — verify the ``X-Internal-API-Key`` header.

    The caller (Sinergia) must include:
        X-Internal-API-Key: <value of FURY_INTERNAL_API_KEY env var>

    Raises HTTP 401 if the key is missing or wrong.
    Returns the key string on success (rarely needed by callers).
    """
    expected = settings.FURY_INTERNAL_API_KEY

    if not expected:
        logger.error("FURY_INTERNAL_API_KEY is not set; refusing all internal requests")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API key is not configured on this server",
        )

    # Constant-time comparison to prevent timing attacks
    import hmac
    if not hmac.compare_digest(provided_key, expected):
        logger.warning("Internal API key mismatch — unauthorized request rejected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )

    return provided_key
