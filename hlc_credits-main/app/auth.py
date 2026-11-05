"""Internal service-to-service auth.

Callers (Durval's video module, Guide) send:
    X-Internal-Key: <LUCA_CREDITS_INTERNAL_KEY>

This is a SEPARATE trust boundary from Guide's FURY key (agreed with Durval 2026-09-22).
⚠️ OPEN with Luis: the platform may standardize on X-Internal-API-Key — if so, flip the
header name here in one place. Constant-time compare, same as the Guide backend.
"""
from __future__ import annotations

import hmac
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

INTERNAL_KEY_HEADER = "X-Internal-Key"
# auto_error=False so a MISSING key returns our structured body too (not FastAPI's plain
# "Not authenticated" string). Durval 2026-09-24: auth errors should carry {code,message}
# like every billing error, so consumers handle them uniformly instead of one-off per client.
_api_key_header = APIKeyHeader(name=INTERNAL_KEY_HEADER, auto_error=False)


def _err(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def verify_internal_key(provided_key: Optional[str] = Security(_api_key_header)) -> str:
    expected = settings.LUCA_CREDITS_INTERNAL_KEY
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            _err("SERVICE_UNAVAILABLE",
                                 "Internal key is not configured on this server; set LUCA_CREDITS_INTERNAL_KEY."))
    if not provided_key:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            _err("FORBIDDEN", f"Missing {INTERNAL_KEY_HEADER} header."))
    if not hmac.compare_digest(provided_key, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            _err("UNAUTHORIZED", f"Invalid {INTERNAL_KEY_HEADER}."))
    return provided_key
