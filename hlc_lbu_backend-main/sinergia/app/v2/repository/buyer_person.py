import logging
from app.tools.strapi import StrapiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BuyerPersonRepository(StrapiClient):
    def __init__(self):
        super(BuyerPersonRepository, self).__init__()
        self.content_type = 'b-person-v2s'

    def get_by_id(self, buyer_person_id: int, populate: list) -> dict:
        params = {
            'filters[id][$eq]': buyer_person_id,
            'populate': populate
        }
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        
        return response.get('data')[0]
    
    def get_by_id_and_brand_and_account(self, buyer_person_id: int, brand_id: int, account_id: int, populate: list = None) -> dict:
        params = {
            'filters[id][$eq]': buyer_person_id,
            'filters[brand_ref][id][$eq]': brand_id,
            'filters[account_ref][id][$eq]': account_id
        }
        if populate is not None:
            params['populate'] = populate
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        
        return response.get('data')[0]