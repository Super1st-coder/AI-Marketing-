import logging
from typing import Any, Dict, Optional
from app.tools.strapi import StrapiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdSetRepository(StrapiClient):
    def __init__(self):
        super(AdSetRepository, self).__init__()
        self.content_type = 'ad-sets'

    def get_by_id(self, ad_set_id, is_fury=False):
        params = {
            'filters[id][$eq]': ad_set_id,
        }

        if is_fury:
            params['populate'] = ['funnel_flow_ref.campaign_ref.brand_ref', 
                                    'funnel_flow_ref.campaign_ref.project_ref.bperson_ref', 
                                    'funnel_flow_ref.campaign_ref.project_ref.product_ref',
                                    'funnel_flow_ref.campaign_ref.ucampaign_ref',
                                    'audiences', 'experiment_ref.subcategory_ref', 
                                    'media_platform_project_id', 'ads']
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        
        return response.get('data')[0]

    def get_by_id_with_ads(self, ad_set_id):
        params = {
            'filters[id][$eq]': ad_set_id,
            'populate': ['ads']
        }
        response = self.get(self.content_type, params)
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        return response['data'][0]

    def update(self, ad_set_id, data):
        payload = {
            'data': data
        }
        endpoint = f"{self.content_type}/{ad_set_id}"
        response = self.put(endpoint, payload)
        
        if not response or not response.get('data'):
            logger.error(f"Failed to update ad set {ad_set_id}")
            return None
        
        return response.get('data')
    
    def get_by_id_and_campaign_and_brand(self, id, campaign_id, brand_id):
        params = {
            'filters[id][$eq]': id,
            'filters[funnel_flow_ref][campaign_ref][id][$eq]': campaign_id,
            'filters[funnel_flow_ref][campaign_ref][brand_ref][id][$eq]': brand_id,
            'populate': ['media_platform_project_id']
        }
        response = self.get(self.content_type, params)
        print(f"Response: {response}")
        
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        
        return response.get('data')[0]

    def get_by_campaign_and_brand_with_selected_ad_channels(
        self, campaign_id: int, brand_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Get the ad sets of a campaign that have at least one selected ad channel.

        Returns the complete Strapi response, preserving its 'data' key as the
        list of ad-set records, or None when the response is falsy or its
        'data' key is absent or empty.
        """
        params = {
            'filters[funnel_flow_ref][campaign_ref][id][$eq]': campaign_id,
            'filters[funnel_flow_ref][campaign_ref][brand_ref][id][$eq]': brand_id,
            'filters[ads][ad_channels][selected][$eq]': 'true',
            'populate': ['ads', 'ads.ad_channels', 'ads.ad_channels.channel_ref'],
        }

        response = self.get(self.content_type, params)

        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None

        return response
