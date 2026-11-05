from typing import Dict, Any, Optional, List
import requests
import os
import logging
from config import config
from app.exceptions.base import StrapiException

logger = logging.getLogger(__name__)

config_type = os.environ.get('CONFIG_TYPE', 'dev')

class StrapiClient:
    """Client for interacting with Strapi API"""

    def __init__(self, base_url: Optional[str] = None):
        cfg = config.get(config_type)
        self.base_url = base_url or getattr(cfg, 'STRAPI_URL', 'http://strapi:1337')
        self.token = getattr(cfg, 'STRAPI_TOKEN', None)

        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

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
            # response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Strapi request failed: {str(e)}")
            raise StrapiException(text=f"Failed to {method} {endpoint}: {str(e)}")

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
        populate: Optional[List[str]] = None,
        pagination: Dict[str, Any] = None,
        sort: Optional[str] = None
    ) -> Dict[str, Any]:
        """Find items by filters"""
        params = {}

        for key, value in filters.items():
            if not isinstance(value, dict):
                params[f"filters[{key}][$eq]"] = value
            else:
                for op, val in value.items():
                    params[f"filters[{key}][{op}]"] = val

        if populate:
            params["populate"] = ",".join(populate)

        if pagination:
            for p_key, p_value in pagination.items():
                params[f"pagination[{p_key}]"] = p_value

        if sort:
            params["sort"] = sort

        return self.get(content_type, params=params)

    # Specific common methods
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
            raise StrapiException(text=f"Campaign Not Found: {campaign_id}")

        return result

    def get_audience_by_adset(self, adset_id: str) -> Dict[str, Any]:
        """Get audience by adset ID"""
        params = {
            "filters[ad_set_ref]": adset_id,
            "populate": "adset_ref"
        }

        logger.info(f"Getting audience: adset_id={adset_id}")
        result = self.get("audience-audiences", params=params)

        if not result.get("data") or len(result["data"]) == 0:
            logger.warning(f"Audience not found: adset_id={adset_id}")
            raise StrapiException(text=f"Audience Not Found for Adset: {adset_id}")

        return result["data"][0]
