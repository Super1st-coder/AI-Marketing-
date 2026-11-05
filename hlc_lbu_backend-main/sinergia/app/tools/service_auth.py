"""Service-to-service API key authentication for Sinergia.

Used exclusively for trusted internal services (e.g. Fury) that need
read-only access to Sinergia data without going through the member
JWT flow or n8n.

Usage:
    @service_api_key_required
    def get(self, ...):
        ...
"""
from functools import wraps
from flask import request
from config import config
import os
import logging

logger = logging.getLogger(__name__)
config_type = os.environ.get('CONFIG_TYPE', 'dev')

def service_api_key_required(f):
    """Decorator that validates X-Service-API-Key header.

    The expected key is read from the FURY_SERVICE_API_KEY environment
    variable.  If the variable is not set, all requests are rejected (fail-
    closed).

    Returns 401 if:
    - The environment variable is not set
    - The header is missing
    - The header value does not match
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        cfg = config.get(config_type)
        expected_key = getattr(cfg, 'FURY_SERVICE_API_KEY', None)

        if not expected_key:
            logger.error(
                "[service_auth] FURY_SERVICE_API_KEY is not set — "
                "rejecting service request."
            )
            return {
                "ok": False,
                "message": {"code": "ESVC001", "text": "Service auth not configured"}
            }, 401

        provided_key = request.headers.get("X-Service-API-Key")

        if not provided_key or provided_key != expected_key:
            logger.warning(
                f"[service_auth] Invalid or missing X-Service-API-Key from {request.remote_addr}"
            )
            return {
                "ok": False,
                "message": {"code": "ESVC002", "text": "Unauthorized service call"}
            }, 401

        return f(*args, **kwargs)
    return decorated
