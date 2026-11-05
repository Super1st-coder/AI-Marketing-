import requests
import os
import logging
from config import config
from app.exceptions.base import FuryException

logger = logging.getLogger(__name__)

config_type = os.environ.get('CONFIG_TYPE', 'dev')

class FuryClient:
    def __init__(self, base_url=None):
        cfg = config.get(config_type)
        self.base_url = base_url or getattr(cfg, 'FURY_URL', 'http://fury:8000')

        # Shared secret for Fury’s internal auth (X-Internal-API-Key).
        # Reads FURY_SERVICE_API_KEY from Sinergia’s own config section [FURY].
        fury_api_key = getattr(cfg, 'FURY_SERVICE_API_KEY', None)
        if not fury_api_key:
            logger.warning(
                "[FuryClient] FURY_SERVICE_API_KEY is not set — "
                "requests to Fury will be rejected with 401/503 once "
                "Fury’s internal auth is enabled."
            )

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **({"X-Internal-API-Key": fury_api_key} if fury_api_key else {}),
        }

    def post(self, endpoint, data):
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Fury request failed: {str(e)}")
            raise FuryException(f"Failed to POST {endpoint}")
        
    def get(self, endpoint, params=None):
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Fury request failed: {str(e)}")
            raise FuryException(f"Failed to GET {endpoint}")
