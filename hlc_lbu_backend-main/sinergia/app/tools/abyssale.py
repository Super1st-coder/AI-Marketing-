import logging
import os
import requests
from typing import Optional, Dict, Any
from config import config
from app.exceptions.base import AbyssaleException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config_type = os.environ.get('CONFIG_TYPE', 'dev')

class AbyssaleClient():
    def __init__(self, base_url: Optional[str] = None):
        cfg = config.get(config_type)
        self.base_url = base_url or getattr(cfg, 'ABYSSALE_URL', 'https://api.abyssale.com')
        self.token = getattr(cfg, 'ABYSSALE_TOKEN', None)
        
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.token:
            self.headers["x-api-key"] = f"{self.token}"

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        file: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Abyssale"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=30,
                files=file
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Abyssale request failed: {str(e)}")
            raise AbyssaleException(text=f"Failed to {method} {endpoint}: {str(e)}")
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request to Abyssale"""
        return self._make_request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST request to Abyssale"""
        return self._make_request("POST", endpoint, data=data)