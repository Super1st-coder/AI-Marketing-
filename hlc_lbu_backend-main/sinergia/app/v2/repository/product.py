from app.tools.strapi import StrapiClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductRepository(StrapiClient):
    def __init__(self):
        super(ProductRepository, self).__init__()
        self.content_type = 'product-v2s'

    def get_by_id(self, product_id, populate=['account_ref']):
        response = super().get_by_id(self.content_type, product_id, populate=populate)
        if not response or not response.get('data'):
            return None
        return response['data']
    
    def get_product_by_id_and_brand_and_account(self, product_id: int, brand_id: int, account_id: int, populate: list = None) -> dict:
        params = {
            'filters[id][$eq]': product_id,
            'filters[brand_ref][id][$eq]': brand_id,
            'filters[account_ref][id][$eq]': account_id
        }
        if populate is not None:
            params['populate'] = populate
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data') or len(response.get('data')) == 0:
            return None
        
        return response.get('data')[0]
