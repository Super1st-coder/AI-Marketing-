import logging
from app.tools.strapi import StrapiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdRepository(StrapiClient):
    def __init__(self):
        super(AdRepository, self).__init__()
        self.content_type = 'ads'

    def get_by_id(self, ad_id, populate: list = None):
        params = {
            'filters[id][$eq]': ad_id
        }

        if populate:
            params['populate'] = populate

        response = self.get(self.content_type, params)
        
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        
        return response.get('data')[0]