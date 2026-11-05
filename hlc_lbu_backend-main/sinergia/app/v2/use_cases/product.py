import logging
import os
from app.exceptions.base import DataNotFoundException, ParametersNotFoundException, IncorrectValidationException, DeleteDataException
from app.v2.repository.product import ProductRepository
from app.v2.repository.account import AccountRepository
from app.v2.repository.product_image import ProductImageRepository
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config_type = os.environ.get('CONFIG_TYPE', 'dev')

class ProductBaseUseCase():
    def __init__(self, user_id = None):
        cfg = config.get(config_type)
        self.region = getattr(cfg, 'REGION_BUCKET', None)
        self.user_id = user_id
        self.product_repository = ProductRepository()
        self.account_repository = AccountRepository()

    def get_docs_bucket_config(self):
        return {'region': self.region}

    def _get_account(self):
        # Buscar account en la base de datos
        account = self.account_repository.get_by_email(self.user_id)
        if not account:
            logger.error(f"Account not found: {self.user_id}")
            raise DataNotFoundException('Account not found')
        return account
    
    def _get_parent_account(self):
        # Validate account
        account = self._get_account()
        parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']
        return parent_account

class GetProductUseCase():
    def __init__(self):
        self.product_repository = ProductRepository()

    def _build_response(self, product: dict) -> dict:
        # Here you can transform the raw product data from the repository into the desired response format
        # For example, you might want to rename fields, calculate additional properties, or filter out sensitive information
        response = {
            'id': product.get('id'),
            'name': product.get('attributes', {}).get('name'),
            'description': product.get('attributes', {}).get('product_story'),
            'benefits': product.get('attributes', {}).get('mandatory_attributes_saved', {}).get('benefits'),
            'features': product.get('attributes', {}).get('mandatory_attributes_saved', {}).get('features'),
            # Add more fields as needed based on the structure of your product data
        }
        return response

    def execute(self, id_product: int) -> dict:
        if not id_product:
            logger.error("Product id is required")
            raise ParametersNotFoundException('Product Id is required')
       
        product = self.product_repository.get_by_id(id_product)

        if not product:
            logger.error(f"Product not found: {id_product}")
            raise DataNotFoundException('Product not found')

        return self._build_response(product)

class DeleteProductImageUseCase(ProductBaseUseCase):
    def __init__(self, user_id):
        super().__init__(user_id)
        self.product_image_repository = ProductImageRepository()

    def execute(self, brand_id: int, product_id: int, thumbnail_id: str) -> dict:
        if not all([brand_id, product_id, thumbnail_id]):
            logger.error("Brand ID, Product ID, and Thumbnail ID are required")
            raise ParametersNotFoundException('Brand ID, Product ID, and Thumbnail ID are required')

        # Get Parent Account
        parent_account = self._get_parent_account()

        # Check if the product exists
        product = self.product_repository.get_product_by_id_and_brand_and_account(product_id, brand_id, parent_account, populate=['images'])
        if not product:
            logger.error(f"Product not found for Brand ID {brand_id} and Product ID {product_id}")
            raise DataNotFoundException('Product not found for the given Brand ID and Product ID')

        # Check if the product is locked
        if product.get('attributes', {}).get('locked', False):
            logger.error(f"Product ID {product_id} is blocked and cannot be modified")
            raise IncorrectValidationException('Product is blocked and cannot be modified')

        # Check if the image exists for the product
        images = product.get('attributes', {}).get('images', {}).get('data', [])
        image_to_delete = next((img for img in images if img.get('attributes', {}).get('thumbnail_id', '') == thumbnail_id), None)
        if not image_to_delete:
            logger.error(f"Image not found for Product ID {product_id} and Thumbnail ID {thumbnail_id}")
            raise DataNotFoundException('Image not found for the given Product ID and Thumbnail ID')

        # Proceed to delete the image
        deleted = self.product_image_repository.delete_by_id(image_to_delete.get('id'))
        if not deleted:
            logger.error(f"Failed to delete Image ID {thumbnail_id} for Product ID {product_id}")
            raise DeleteDataException('Failed to delete the image')
        
        logger.info(f"User {self.user_id} deleted Image ID {thumbnail_id} from Product ID {product_id}")

        return {}