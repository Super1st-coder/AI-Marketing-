from app.tools.strapi import StrapiClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CampaignChannelPublishRepository(StrapiClient):
    """Repository for campaign channel publish-related operations."""
    def __init__(self):
        super(CampaignChannelPublishRepository, self).__init__()
        self.content_type = 'campaign-channel-publishes'

    def create(self, data):
        """Create a new campaign channel publish."""
        payload = {
            'data': data
        }

        response = self.post(self.content_type, payload)
        if not response or not response.get('data'):
            logger.error(f"Failed to create campaign channel publish {response}")
            return None
        
        return response.get('data')
    
    def update(self, publish_id, data):
        """Update an existing campaign channel publish by ID."""
        payload = {
            'data': data
        }

        endpoint = f"{self.content_type}/{publish_id}"
        response = self.put(endpoint, payload)
        if not response or not response.get('data'):
            return None
        
        return response.get('data')
    
    def save_or_update(self, filter_data, update_data):
        """Save or update a campaign channel publish based on filters."""
        existing = self.find_by_filters(self.content_type, filter_data)
        
        if not existing or not len(existing.get('data', [])) > 0:
            # Create new record
            created = self.create({**update_data, **filter_data})
            logger.info(f"Campaign channel publish created")
            return created
        else:
            # Update existing record
            updated = self.update(existing.get('data')[0].get('id'), update_data)
            logger.info(f"Campaign channel publish updated")
            return updated
        
    def get_by_campaign_id_and_channel_id(self, campaign_id: int, channel_id: int):
        """Get campaign channel publishes by campaign ID and channel ID."""
        params = {
            'filters[campaign_id][id][$eq]': campaign_id,
            'filters[channel_id][id][$eq]': channel_id,
        }

        response = self.get(self.content_type, params)

        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None

        return response.get('data')[0]

    def get_by_meta_campaign_id_and_brand_account(self, meta_campaign_id, parent_account):
        """Get the publish mapping by Meta campaign ID, brand, and account parent."""
        params = {
            'filters[meta_campaign_id][$eq]': str(meta_campaign_id),
            'filters[campaign_id][account_ref][id][$eq]': parent_account,
            'populate': 'campaign_id,campaign_id.brand_ref,campaign_id.project_ref,campaign_id.project_ref.product_ref,campaign_id.project_ref.bperson_ref,campaign_id.ucampaign_ref',
        }

        response = self.get(self.content_type, params)
        if response and response.get('data') and len(response.get('data')) > 0:
            return response.get('data')[0]

        return None

            

