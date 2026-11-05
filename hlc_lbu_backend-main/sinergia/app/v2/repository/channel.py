from app.tools.strapi import StrapiClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChannelRepository(StrapiClient):
    def __init__(self):
        super(ChannelRepository, self).__init__()
        self.content_type = 'channel-v2s'

    def get_by_name(self, name):
        # Filter by name lower case to avoid case sensitivity issues
        filters = {
            'filters[name][$eqi]': name.lower()
        }
        response = self.get(self.content_type, filters)
        if not response or not response.get('data'):
            return None
        return response['data'][0]
