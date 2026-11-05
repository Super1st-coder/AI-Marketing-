import logging
from app.tools.strapi import StrapiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BuyerMainImageRepository(StrapiClient):
    """Repository for Buyer Main Image interactions."""
    def __init__(self):
        super(BuyerMainImageRepository, self).__init__()
        self.content_type = 'buyer-main-images'

    def create(self, data: dict) -> dict:
        """Create a new buyer main image record."""
        payload = {
            'data': data
        }
        response = self.post(self.content_type, payload)
        
        if not response or not response.get('data'):
            return None
        
        return response.get('data')
    
    def delete_by_id_and_buyer_person_id(self, buyer_main_image_id: int, buyer_person_id: int) -> bool:
        """ Soft Delete a buyer main image by ID and buyer person ID.
            This method sets the status to 'I' (Deleted) instead of removing the record from the database.
        """        
        # Update the status to 'I' for soft delete
        update_data = {
            'status': 'I',
            'selected': False  # Deseleccionar la imagen principal al eliminarla
        }
        endpoint = f"{self.content_type}/{buyer_main_image_id}"
        response = self.put(endpoint, {'data': update_data})
        
        if not response or not response.get('data'):
            logger.error(f"Failed to soft delete buyer main image {buyer_main_image_id} for buyer person {buyer_person_id}")
            return False
        
        return True

    def get_by_id(self, buyer_main_image_id: int) -> dict:
        """Get a buyer main image by ID."""
        response = self.get(f"{self.content_type}/{buyer_main_image_id}")
        
        if not response or not response.get('data'):
            return None
        
        return response.get('data')
    
    def get_by_id_and_buyer_person_id(self, buyer_main_image_id: int, buyer_person_id: int) -> dict:
        """Get a buyer main image by ID and buyer person ID. And status active."""
        params = {
            'filters[id][$eq]': buyer_main_image_id,
            'filters[bperson_id][id][$eq]': buyer_person_id,
            'filters[status][$eq]': 'A',
            'populate': ['variant_images']
        }
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data'):
            return None
        
        data = response.get('data')
        return data[0] if data else None
    
    def get_by_buyer_person_id(self, buyer_person_id: int) -> list:
        """Get all main images for a given buyer person ID. And status active."""
        params = {
            'filters[bperson_id][id][$eq]': buyer_person_id,
            'filters[status][$eq]': 'A',
            'populate': ['variant_images'],
            'pagination[pageSize]': 200
        }
        response = self.get(self.content_type, params)
        
        if not response or not response.get('data'):
            return []
        
        return response.get('data')
    
    def get_by_buyer_person_id_and_image_id(self, buyer_person_id: int, image_id: str, populate: list = None) -> dict:
        """Get a main image for a given buyer person ID and image ID. And status active."""
        params = {
            'filters[bperson_id][id][$eq]': buyer_person_id,
            'filters[image_id][$eq]': image_id,
            'filters[status][$eq]': 'A'
        }

        if populate:
            params['populate'] = populate

        response = self.get(self.content_type, params)
        
        if not response or not response.get('data'):
            return None
        
        data = response.get('data')
        return data[0] if data else None
