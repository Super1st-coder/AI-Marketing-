from app.tools.strapi import StrapiClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CampaignRepository(StrapiClient):
    """Repository for campaign-related operations."""
    def __init__(self):
        super(CampaignRepository, self).__init__()
        self.content_type = 'campaigns'

    def get_by_id(self, campaign_id):
        """Get a campaign by ID."""
        params = {
            'filters[id][$eq]': campaign_id
        }
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        
        return response.get('data')[0]

    def get_by_id_and_brand(self, campaign_id, brand_id):
        """Get a campaign by ID and brand ID."""
        params = {
            'filters[id][$eq]': campaign_id,
            'filters[brand_ref][id][$eq]': brand_id
        }
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        
        return response.get('data')[0]

    def get_by_id_brand_and_account(self, campaign_id, brand_id, account_id):
        """Get a campaign by ID, brand ID, and account ID."""
        params = {
            'filters[id][$eq]': campaign_id,
            'filters[brand_ref][id][$eq]': brand_id,
            'filters[account_ref][id][$eq]': account_id
        }
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        
        return response.get('data')[0]