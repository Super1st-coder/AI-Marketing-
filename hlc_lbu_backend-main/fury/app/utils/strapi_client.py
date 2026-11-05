"""Strapi client utility"""
from typing import Dict, Any, Optional, List
import requests
from core.config import settings
from core.exceptions import StrapiException
from core.logging import get_logger

logger = get_logger(__name__)


class StrapiClient:
    """Client for interacting with Strapi API"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.STRAPI_URL
        self.token = settings.STRAPI_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Strapi"""
        url = f"{self.base_url}/api/{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Strapi request failed: {str(e)}")
            raise StrapiException(
                message=f"Failed to {method} {endpoint}",
                details={"error": str(e)}
            )
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request to Strapi"""
        return self._make_request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST request to Strapi"""
        return self._make_request("POST", endpoint, data=data)
    
    def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """PUT request to Strapi"""
        return self._make_request("PUT", endpoint, data=data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request to Strapi"""
        return self._make_request("DELETE", endpoint)
    
    def get_ad_channel(self, ad_id: int, channel_id: int) -> Dict[str, Any]:
        """Get ad channel with filters"""
        params = {
            "filters[ad_ref][id]": ad_id,
            "filters[channel_ref][id]": channel_id,
            "populate": "ad_ref,channel_ref.channel_group_ref"
        }
        
        logger.info(f"Getting ad channel: ad_id={ad_id}, channel_id={channel_id}")
        result = self.get("ad-channels", params=params)
        
        if not result.get("data") or len(result["data"]) == 0:
            logger.warning(f"Ad channel not found: ad_id={ad_id}, channel_id={channel_id}")
            raise StrapiException(
                message="Ad Channel Not Found",
                details={"ad_id": ad_id, "channel_id": channel_id}
            )
        
        return result
    
    def get_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Get campaign with all relationships"""
        params = {
            "filters[id]": campaign_id,
            "populate": "ucampaign_ref,funnel_ref,project_ref.bperson_ref,project_ref.product_ref"
        }
        
        logger.info(f"Getting campaign: campaign_id={campaign_id}")
        result = self.get("campaigns", params=params)
        
        if not result.get("data") or len(result["data"]) == 0:
            logger.warning(f"Campaign not found: campaign_id={campaign_id}")
            raise StrapiException(
                message="Campaign Not Found",
                details={"campaign_id": campaign_id}
            )
        
        return result
    
    def get_by_id(self, content_type: str, item_id: str, populate: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get item by ID with optional population"""
        params = {}
        if populate:
            params["populate"] = ",".join(populate)
        
        return self.get(f"{content_type}/{item_id}", params=params)
    
    def find_by_filters(
        self,
        content_type: str,
        filters: Dict[str, Any],
        populate: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Find items by filters"""
        params = {}
        
        for key, value in filters.items():
            params[f"filters[{key}][$eq]"] = value
        
        if populate:
            params["populate"] = ",".join(populate)
        
        return self.get(content_type, params=params)

