import logging
from app.tools.strapi import StrapiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BuyerVariantImageRepository(StrapiClient):
    """Repository for Buyer Variant Image interactions."""
    def __init__(self):
        super(BuyerVariantImageRepository, self).__init__()
        self.content_type = 'buyer-variant-images'

    def delete_by_id(self, buyer_variant_image_id: int) -> bool:
        """ Soft Delete a buyer variant image by ID.
            This method sets the status to 'I' (Deleted) instead of removing the record from the database.
        """        
        # Update the status to 'I' for soft delete
        update_data = {
            'status': 'I'
        }
        endpoint = f"{self.content_type}/{buyer_variant_image_id}"
        response = self.put(endpoint, {'data': update_data})
        
        if not response or not response.get('data'):
            logger.error(f"Failed to soft delete buyer variant image {buyer_variant_image_id}")
            return False
        
        return True
    
    def create(self, buyer_variant_image_data: dict) -> dict:
        """Create a new buyer variant image record in Strapi."""
        response = self.post(self.content_type, {'data': buyer_variant_image_data})

        if not response or not response.get('data'):
            logger.error(f"Failed to create buyer variant image with data: {buyer_variant_image_data}")
            return None

        return response['data']

    def get_by_main_image_id(self, main_image_id: int, status: list = ['A']) -> list:
        """Get all variant images for a given main image ID (status in ['A'] by default)."""
        params = {
            'filters[main_image_id][id][$eq]': main_image_id,
            'pagination[pageSize]': 200
        }

        if status:
            params['filters[status][$in]'] = status

        response = self.get(self.content_type, params)

        if not response or not response.get('data'):
            return []

        return response.get('data')

    def set_selected(self, buyer_variant_image_id: int) -> bool:
        """Mark a buyer variant image as selected (Strapi 'status' field)."""
        # Update the status to 'A' for selected
        update_data = {
            'status': 'A'
        }
        endpoint = f"{self.content_type}/{buyer_variant_image_id}"
        response = self.put(endpoint, {'data': update_data})

        if not response or not response.get('data'):
            logger.error(f"Failed to set selected on buyer variant image {buyer_variant_image_id}")
            return False

        return True

    def get_by_buyer_person_id_and_image_id(self, buyer_person_id: int, image_id: str, populate: list = None) -> dict:
        """Get a buyer variant image by buyer person ID and image ID."""
        params = {
            'filters[main_image_id][bperson_id][id][$eq]': buyer_person_id,
            'filters[image_id][$eq]': image_id
            # 'filters[status][$eq]': 'A'
        }

        if populate:
            params['populate'] = populate

        response = self.get(self.content_type, params)

        if not response or not response.get('data'):
            return None
        
        data = response.get('data')
        return data[0] if data else None
