import os
import requests
import logging

from config import config
from typing import Dict, Any, Optional, List
from app.exceptions.base import ImageLibraryException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config_type = os.environ.get('CONFIG_TYPE', 'dev')

class ImageLibraryClient:
    """Client for interacting with Image Library API"""
    
    def __init__(self, base_url: Optional[str] = None):
        cfg = config.get(config_type)
        self.base_url = base_url or getattr(cfg, 'IMAGE_LIBRARY_URL', 'http://image-library:8000')
        self.token = getattr(cfg, 'IMAGE_LIBRARY_TOKEN', None)
        
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
        """Make HTTP request to Image Library"""
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
            # response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Image Library request failed: {str(e)}")
            raise ImageLibraryException(text=f"Failed to {method} {endpoint}: {str(e)}")
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request to Image Library"""
        return self._make_request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST request to Image Library"""
        return self._make_request("POST", endpoint, data=data)
    
    def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """PUT request to Image Library"""
        self.headers.update({'x-amz-server-side-encryption': 'AES256'})
        return self._make_request("PUT", endpoint, file=data)