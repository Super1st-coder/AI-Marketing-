"""
Authentication & authorization utilities for the API.

Currently supports:

1. **Internal API key** (``verify_internal_api_key``)
   Used to secure endpoints so that only internal microservices (like Sinergia) can call them.
   The caller must send:
       ``X-Internal-API-Key: <FURY_INTERNAL_API_KEY>``
   The key is configured via the env var ``FURY_INTERNAL_API_KEY``.

Environment variables required:
    FURY_INTERNAL_API_KEY   — shared secret for internal service-to-service calls
"""
from __future__ import annotations

import hmac
from typing import Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Security scheme objects (used by FastAPI's OpenAPI UI / Swagger)
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=True)

# ---------------------------------------------------------------------------
# Mechanism 1 — Internal API key
# ---------------------------------------------------------------------------

def verify_internal_api_key(
    provided_key: str = Security(_api_key_header),
) -> str:
    """FastAPI dependency — verify the ``X-Internal-API-Key`` header.

    The caller must include:
        X-Internal-API-Key: <value of FURY_INTERNAL_API_KEY env var>

    Raises HTTP 401 if the key is missing or wrong.
    Returns the key string on success.
    """
    expected = settings.FURY_INTERNAL_API_KEY

    if not expected:
        logger.error("FURY_INTERNAL_API_KEY is not set; refusing all internal requests")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API key is not configured on this server",
        )

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(provided_key, expected):
        logger.warning("Internal API key mismatch — unauthorized request rejected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )

    return provided_key
