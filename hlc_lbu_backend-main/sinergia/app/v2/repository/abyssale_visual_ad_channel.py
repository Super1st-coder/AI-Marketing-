from app.tools.strapi import StrapiClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AbyssaleVisualAdChannelRepository(StrapiClient):
    """Repository for abyssale visual ad-channel mappings."""

    def __init__(self):
        super(AbyssaleVisualAdChannelRepository, self).__init__()
        self.content_type = 'abyssale-visual-ad-channels'

    def get_by_sharing_id(self, sharing_id):
        """Get the visual mapping by sharing ID and populate its ad channel relation."""
        params = {
            'filters[sharing_id][$eq]': sharing_id,
            'populate': 'ad_channel'
        }

        response = self.get(self.content_type, params)

        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None

        return response.get('data')[0]
