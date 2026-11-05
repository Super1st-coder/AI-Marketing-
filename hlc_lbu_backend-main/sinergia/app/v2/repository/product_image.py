from app.tools.strapi import StrapiClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductImageRepository(StrapiClient):
    """Repository for product image records."""

    def __init__(self):
        super(ProductImageRepository, self).__init__()
        self.content_type = 'product-images'

    def get_by_product_id(self, product_id):
        """Get all product image records associated to a product."""
        params = {
            'filters[product_ref][id][$eq]': product_id
        }

        response = self.get(self.content_type, params)
        if not response or not response.get('data'):
            return []

        return response.get('data')

    def delete_by_id(self, product_image_id: int) -> bool:
        """ Hard Delete a product image by ID.
            This method remove the record from the database.
        """
        endpoint = f"{self.content_type}/{product_image_id}"
        response = self.delete(endpoint)
        
        if not response or not response.get('data'):
            logger.error(f"Failed to delete product image {product_image_id}")
            return False
        
        return True
