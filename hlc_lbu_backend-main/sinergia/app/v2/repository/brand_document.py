import logging
from app.tools.strapi import StrapiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrandDocumentRepository(StrapiClient):
    def __init__(self):
        super(BrandDocumentRepository, self).__init__()
        self.content_type = 'brand-documents'

    def get_all(self, data):
        filters = data.get('filters', {})
        populate = data.get('populate', [])
        response = self.find_by_filters(self.content_type, filters, populate)
        return response
    
    def create(self, data):
        payload = {'data': data}
        response = self.post(self.content_type, payload)
        return response
    
    def delete_entry(self, entry_id):
        response = self.delete(f"{self.content_type}/{entry_id}")
        return response