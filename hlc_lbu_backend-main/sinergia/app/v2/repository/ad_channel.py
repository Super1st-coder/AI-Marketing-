from app.tools.strapi import StrapiClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdChannelRepository(StrapiClient):
    """Repository for ad channel-related operations."""

    _NAME_POPULATE_PARAMS = {
        'populate[ad_ref2][fields][0]': 'name',
        'populate[ad_ref2][populate][ad_set_ref2][fields][0]': 'name',
        'populate[channel_ref][fields][1]': 'name',
    }

    def __init__(self):
        super(AdChannelRepository, self).__init__()
        self.content_type = 'ad-channels'

    def update(self, ad_channel_id, data):
        """Update an ad channel by ID."""
        payload = {
            'data': data
        }

        endpoint = f"{self.content_type}/{ad_channel_id}"
        response = self.put(endpoint, payload)
        if not response or not response.get('data'):
            return None
        
        return response.get('data')
    
    def create(self, data):
        response = self.post(self.content_type, {'data': data})
        if not response or not response.get('data'):
            return None
        return response['data']

    def get_by_campaign_and_ad_channel_id(
        self, campaign_id: int, adset_id: int, ad_id: int, adchannel_id: int,
        populate_names: bool = False,
    ):
        """Get an ad channel by campaign ID, ad set ID, ad ID, and ad channel ID."""
        params = {
            'filters[id][$eq]': adchannel_id,
            'filters[ad_ref2][id][$eq]': ad_id,
            'filters[ad_ref2][ad_set_ref2][id][$eq]': adset_id,
            'filters[ad_ref2][ad_set_ref2][funnel_flow_ref][campaign_ref][id][$eq]': campaign_id,
            'populate[channel_ref][fields][0]': 'id'
        }

        if populate_names:
            params.update(self._NAME_POPULATE_PARAMS)
        
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        
        return response.get('data')[0]

    def get_by_ad_and_channel_id(self, ad_id: int, channel_id: int):
        """Get ad channels by ad ID and channel ID."""
        params = {
            'filters[ad_ref2][id][$eq]': ad_id,
            'filters[channel_ref][id][$eq]': channel_id
        }
        
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data'):
            return []
        
        return response.get('data')

    def get_by_id_and_ad_and_channel(self, ad_channel_id: int, ad_id: int, channel_id: int, populate: list = None):
        """Get an ad channel by ID, ad ID, and channel ID."""
        params = {
            'filters[id][$eq]': ad_channel_id,
            'filters[ad_ref2][id][$eq]': ad_id,
            'filters[channel_ref][id][$eq]': channel_id
        }

        if populate:
            params['populate'] = populate
        
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        
        return response.get('data')[0]

    def get_by_id_ad_campaign_and_channel(self, ad_channel_id: int, ad_id: int, campaign_id: int, channel_id: int):
        """Get an ad channel by ID, ad ID, campaign ID, and channel ID."""
        params = {
            'filters[id][$eq]': ad_channel_id,
            'filters[ad_ref2][id][$eq]': ad_id,
            'filters[ad_ref2][ad_set_ref2][funnel_flow_ref][campaign_ref][id][$eq]': campaign_id,
            'filters[channel_ref][id][$eq]': channel_id
        }

        response = self.get(self.content_type, params)

        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None

        return response.get('data')[0]

    def delete_by_id(self, ad_channel_id):
        """Delete an ad channel by ID."""
        endpoint = f"{self.content_type}/{ad_channel_id}"
        response = self.delete(endpoint)
        if not response or not response.get('data'):
            return None
        return response.get('data')
    
    def get_ad_by_id(self, id):
        """Get ad channels by ID."""
        params = {
            'filters[id][$eq]': id,
        }
        
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        
        return response.get('data')[0]

