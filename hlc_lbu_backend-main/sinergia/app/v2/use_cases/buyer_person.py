import logging
import mimetypes
import os
import time
from base64 import b64decode, b64encode
from io import BytesIO
from retrying import retry
from app.exceptions.base import DataAlreadyRegisteredException, ParametersNotFoundException, DataNotFoundException, IncorrectValidationException, SinergiaException, ImageLibraryException, S3ClientException
from app.v2.repository.buyer_person import BuyerPersonRepository
from app.v2.repository.buyer_main_image import BuyerMainImageRepository
from app.v2.repository.buyer_variant_image import BuyerVariantImageRepository
from app.v2.repository.account import AccountRepository
from app.v2.repository.product import ProductRepository
from app.v2.repository.image_library import ImageLibraryRepository
from app.v2.models.constant import ALLOWED_PHOTOGRAPHY_EFFECTS, BUYER_IMAGE_VARIANT_LABELS, ALLOWED_VISUAL_STYLES
from app.v1.repository.base import N8NClient
from app.tools.fury import FuryClient
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config_type = os.environ.get('CONFIG_TYPE', 'dev')

class BuyerParsonBaseUseCase():
    def __init__(self, user_id = None):
        self.buyer_person_repository = BuyerPersonRepository()
        self.account_repository = AccountRepository()
        self.user_id = user_id
        cfg = config.get(config_type)
        self.region = getattr(cfg, 'REGION_BUCKET', None)

    def get_docs_bucket_config(self):
        return {'region': self.region}

    def _get_account(self):
        # Buscar account en la base de datos
        account = self.account_repository.get_by_email(self.user_id)
        if not account:
            logger.error(f"Account not found: {self.user_id}")
            raise DataNotFoundException('Account not found')
        return account
    
    def _get_extention_from_mime(self, mime_type):
        ext = mimetypes.guess_extension(mime_type)
        if not ext:
            ext = '.jpg'  # Default to .jpg if MIME type is unknown
        return ext
    
    def _get_parent_account(self):
        # Validate account
        account = self._get_account()
        parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']
        return parent_account
    
class GetBuyerPersonUseCase(BuyerParsonBaseUseCase):
    def __init__(self):
        super().__init__()

    def _build_response(self, buyer_person: dict) -> dict:
        # Here you can transform the raw buyer person data from the repository into the desired response format
        # For example, you might want to rename fields, calculate additional properties, or filter out sensitive information
        response = {
            'id': buyer_person.get('id'),
            'name': buyer_person.get('attributes', {}).get('name'),
            'story': buyer_person.get('attributes', {}).get('bperson_story'),
            'age_range': buyer_person.get('attributes', {}).get('mandatory_attributes_saved', {}).get('age_range'),
            'gender': buyer_person.get('attributes', {}).get('mandatory_attributes_saved', {}).get('gender'),
            'hometown': buyer_person.get('attributes', {}).get('mandatory_attributes_saved', {}).get('hometown'),
            'pain_points': buyer_person.get('attributes', {}).get('mandatory_attributes_saved', {}).get('pain_points'),
            'customer_goals': buyer_person.get('attributes', {}).get('mandatory_attributes_saved', {}).get('customer_goals'),
            'fears_and_worries': buyer_person.get('attributes', {}).get('mandatory_attributes_saved', {}).get('fears_and_worries'),
            'income_level_brackets': buyer_person.get('attributes', {}).get('mandatory_attributes_saved', {}).get('income_level_brackets'),
            'barriers_to_making_a_change': buyer_person.get('attributes', {}).get('mandatory_attributes_saved', {}).get('barriers_to_making_a_change'),
            'visual_archetype': buyer_person.get('attributes', {}).get('mandatory_attributes_saved', {}).get('name_and_nickname'),
            # Add more fields as needed based on the structure of your buyer person data
        }
        return response

    def execute(self, buyer_person_id: int) -> dict:
        if not buyer_person_id:
            logger.error("Buyer Person id is required")
            raise ParametersNotFoundException('Buyer Person Id is required')
       
        populate = None
        buyer_person = self.buyer_person_repository.get_by_id(buyer_person_id, populate)

        if not buyer_person:
            logger.error(f"Buyer Person not found: {buyer_person_id}")
            raise DataNotFoundException('Buyer Person not found')

        return self._build_response(buyer_person)
    
class UploadMainImageBuyerPersonUseCase(BuyerParsonBaseUseCase):
    """Fury Tool: Use case for uploading main images to a buyer person."""
    def __init__(self):
        super().__init__()
        self.image_library_repository = ImageLibraryRepository()
        self.buyer_main_image_repository = BuyerMainImageRepository()
        self.n8nClient = N8NClient()

    def _validate_payload(self, payload: dict) -> None:
        """Validate the payload structure and types."""
        if not payload or not isinstance(payload, dict):
            logger.error(f"Invalid payload: {payload}")
            raise IncorrectValidationException('Invalid payload')
        
        required_fields = ['image_data', 'image_name', 'mime_type', 'image_prompt']
        for field in required_fields:
            if field not in payload:
                logger.error(f"Missing required field: {field}")
                raise IncorrectValidationException(f"Missing required field: {field}")
        
        # Validate field types
        if not isinstance(payload.get('image_data'), str):
            logger.error(f"image_data must be a string (base64), got {type(payload.get('image_data'))}")
            raise IncorrectValidationException('image_data must be a string (base64)')
        
        if not isinstance(payload.get('image_name'), str):
            logger.error(f"image_name must be a string, got {type(payload.get('image_name'))}")
            raise IncorrectValidationException('image_name must be a string')
        
        if not isinstance(payload.get('mime_type'), str):
            logger.error(f"mime_type must be a string, got {type(payload.get('mime_type'))}")
            raise IncorrectValidationException('mime_type must be a string')
        
        if not isinstance(payload.get('image_prompt'), str):
            logger.error(f"image_prompt must be a string, got {type(payload.get('image_prompt'))}")
            raise IncorrectValidationException('image_prompt must be a string')

    @retry(wait_fixed=5000, stop_max_attempt_number=4)
    def get_image_url(self, image_id: str) -> str:
        """Get the image URL from Image Library."""
        logger.debug(f"Getting image url for id: {image_id}")
        url_response = self.image_library_repository.get_image(image_id)
        if not url_response.get('url'):
            logger.error(f"Image not found: {image_id}")
            raise ImageLibraryException('Image not found')
        return url_response.get('url')

    def execute(self, buyer_person_id: int, payload: dict) -> dict:
        """Upload a main image for a buyer person.
        
        Args:
            buyer_person_id (int): ID of the buyer person
            payload (dict): Payload containing image_data (base64), image_name, mime_type, image_prompt
            
        Returns:
            dict: Created buyer main image record
        """
        try:
            logger.debug(f"Uploading main image for buyer person: {buyer_person_id}")
            
            # Validate payload
            self._validate_payload(payload)
            
            # Validate buyer person exists
            populate = ['brand_ref', 'account_ref']
            buyer_person = self.buyer_person_repository.get_by_id(buyer_person_id, populate=populate)
            if not buyer_person:
                logger.error(f"Buyer Person not found: {buyer_person_id}")
                raise DataNotFoundException('Buyer Person not found')
            
            # Get parent account from buyer person
            account = buyer_person.get('attributes', {}).get('account_ref', {}).get('data', {})
            parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']
            
            if not parent_account:
                logger.error(f"Account not found for Buyer Person: {buyer_person_id}")
                raise DataNotFoundException('Account not found for Buyer Person')
            
            brand_id = buyer_person.get('attributes', {}).get('brand_ref', {}).get('data', {}).get('id')
            if not brand_id:
                logger.error(f"Brand not found for Buyer Person: {buyer_person_id}")
                raise DataNotFoundException('Brand not found for Buyer Person')

            # Decodificar base64 a bytes
            try:
                image_data = payload.get('image_data', '')
                # El valor puede venir con prefijo "data:{mime};base64,"
                if isinstance(image_data, str) and image_data.startswith('data:'):
                    comma_idx = image_data.find(',')
                    if comma_idx != -1:
                        image_data = image_data[comma_idx + 1:]

                image_bytes = b64decode(image_data)
            except Exception as e:
                logger.error(f"Invalid base64 image data: {e}")
                raise ParametersNotFoundException('Invalid base64 image data')

            # Crear buffer
            buffer = BytesIO(image_bytes)
            buffer.seek(0)

            # Subir imagen
            try:
                content_type = payload['mime_type']
                filename = f"{payload['image_name']}{self._get_extention_from_mime(content_type)}"
                params = { 'brand_id' : brand_id, 'buyer_id': buyer_person_id, 
                        'account_id': parent_account, 'category': 'buyer',
                        'type': 'original', 'subcategory': 'main' }
            
                files = { 
                    'file' : (filename, buffer, content_type)#,
                }
                response = self.n8nClient.executePost('/webhook/v2/buyer_person/image/main/upload',{},False,is_binary=False,params=params,files=files)
                image_id = response.get('data', {}).get('image_id')
            except Exception as e:
                logger.error(f"Error uploading image: {e}")
                raise e
            
            # Create buyer main image record
            buyer_main_image_data = {
                'image_id': image_id,
                # 'image_url': image_url,
                'prompt': payload['image_prompt'],
                'selected': False,
                'bperson_id': buyer_person_id
            }
            
            created_image = self.buyer_main_image_repository.create(buyer_main_image_data)
            if not created_image:
                logger.error(f"Error creating buyer main image record")
                raise SinergiaException('Error creating buyer main image record')
            
            logger.debug(f"Buyer main image created successfully: {created_image.get('id')}")

            return {'image_id': created_image.get('attributes', {}).get('image_id', '')}
            
        except SinergiaException as e:
            logger.error(f"Error uploading buyer person main image: {e.text}")
            raise e
        except ImageLibraryException as e:
            logger.error(f"Error uploading buyer person main image: {e}")
            raise e
        except Exception as err:
            logger.error(f"Error uploading buyer person main image: {err}")
            raise SinergiaException('Error uploading buyer person main image')
    
class GenerateMainImagesAutomaticUseCase(BuyerParsonBaseUseCase):
    def __init__(self, user_id):
        super().__init__(user_id)
        self.n_variations = 4  # Default number of variations to generate
        self.fury_client = FuryClient()
        self.product_repository = ProductRepository()

    def execute(self, payload: dict) -> dict:
        # Validate payload structure
        if not payload or not isinstance(payload, dict):
            raise IncorrectValidationException('Invalid payload')
        
        # Validar que el payload tenga los campos requeridos
        required_fields = ['brand_id', 'bperson_id']

        for field in required_fields:
            if field not in payload:
                logger.error(f"Missing required field: {field}")
                raise IncorrectValidationException(f"Missing required field: {field}")
        
        brand_id = payload.get('brand_id')
        buyer_person_id = payload.get('bperson_id')
        product_id = payload.get('product_id')

        # Get Parent Account
        parent_account = self._get_parent_account()

        if not buyer_person_id:
            logger.error("Buyer Person id is required")
            raise ParametersNotFoundException('Buyer Person Id is required')
        
        # Buscar Buyer Person en la base de datos por id, brand_ref y account_ref
        buyer_person = self.buyer_person_repository.get_by_id_and_brand_and_account(buyer_person_id=buyer_person_id, brand_id=brand_id, account_id=parent_account)
        if not buyer_person:
            logger.error(f"Buyer Person not found: {buyer_person_id} for brand {brand_id} and account {parent_account}")
            raise DataNotFoundException('Buyer Person not found for the given brand and account')
        
        if product_id:
            # Buscar Product en la base de datos por id, brand_ref y account_ref
            product = self.product_repository.get_product_by_id_and_brand_and_account(product_id=product_id, brand_id=brand_id, account_id=parent_account)
            if not product:
                logger.error(f"Product not found: {product_id} for brand {brand_id} and account {parent_account}")
                raise DataNotFoundException('Product not found for the given brand and account')
        
        try:
            response = self.fury_client.post('/api/v2/persona-images', {'id_buyer_persona': buyer_person_id,
                                                                        'n_variations': self.n_variations, 
                                                                        'id_product': product_id})
            return {'job_id': response.get('data', {}).get('task_id')}
        except Exception as e:
            logger.error(f"Error generating Buyer Person Main Images variations: {str(e)}")
            raise e

class GetMainImagesUseCase(BuyerParsonBaseUseCase):
    def __init__(self, user_id):
        super().__init__(user_id)
        self.buyer_main_image_repository = BuyerMainImageRepository()
        self.image_library_repository = ImageLibraryRepository()
    
    def _build_response(self, buyer_person_id: int, main_images: list) -> dict:
        # Build response
        images_response = []
        for image in main_images:
            images_response.append({
                'id': image.get('id'),
                'image_id': image.get('attributes', {}).get('image_id'),
                'image_url': image.get('attributes', {}).get('image_url'),
                'prompt': image.get('attributes', {}).get('prompt'),
                'selected': image.get('attributes', {}).get('selected'),
                'has_variants': len([variant_image for variant_image in image.get('attributes', {}).get('variant_images', {}).get('data', []) if variant_image.get('attributes', {}).get('status', 'I') == 'A']) > 0
            })
        
        response = {
            'id': buyer_person_id,
            'main_images': images_response
        }
        return response
    
    def execute(self, brand_id: int, buyer_person_id: int) -> dict:
        if not brand_id:
            logger.error("Brand id is required")
            raise ParametersNotFoundException('Brand Id is required')

        if not buyer_person_id:
            logger.error("Buyer Person id is required")
            raise ParametersNotFoundException('Buyer Person Id is required')

        # Get Parent Account
        parent_account = self._get_parent_account()
        
        # Buscar Buyer Person en la base de datos por id, brand_ref y account_ref
        buyer_person = self.buyer_person_repository.get_by_id_and_brand_and_account(buyer_person_id=buyer_person_id, brand_id=brand_id, account_id=parent_account)
        if not buyer_person:
            logger.error(f"Buyer Person not found: {buyer_person_id} for brand {brand_id} and account {parent_account}")
            raise DataNotFoundException('Buyer Person not found for the given brand and account')

        main_images = self.buyer_main_image_repository.get_by_buyer_person_id(buyer_person_id)

        # Obtener las urls prefirmadas por cada image_id de main_images
        for image in main_images:
            try:
                image_id = image.get('attributes', {}).get('image_id')
                if image_id:
                    image_url = self.image_library_repository.get_image(image_id)
                    image['attributes']['image_url'] = image_url.get('url') if image_url else None
                else:
                    logger.warning(f"Image ID not found for buyer main image record: {image.get('id')}")
            except Exception as e:
                logger.error(f"Error getting image URL for image ID {image_id}: {e}")
                image['attributes']['image_url'] = None  # Set to None or some default value if URL retrieval fails

        # Build response
        response = self._build_response(buyer_person_id, main_images)

        return response

class GetVariantImagesUseCase(BuyerParsonBaseUseCase):
    """List the variant images of a given base (main) image for a buyer person."""
    def __init__(self, user_id):
        super().__init__(user_id)
        self.buyer_main_image_repository = BuyerMainImageRepository()
        self.buyer_variant_image_repository = BuyerVariantImageRepository()
        self.image_library_repository = ImageLibraryRepository()

    def _build_response(self, buyer_person_id: int, base_image_id: str, variant_images: list) -> dict:
        variants_response = []
        for image in variant_images:
            variants_response.append({
                'id': image.get('id'),
                'image_id': image.get('attributes', {}).get('image_id'),
                'image_url': image.get('attributes', {}).get('image_url'),
                'label': image.get('attributes', {}).get('label'),
                'prompt': image.get('attributes', {}).get('prompt'),
                'status': image.get('attributes', {}).get('status'),
            })

        return {
            'id': buyer_person_id,
            'base_image_id': base_image_id,
            'variants': variants_response
        }

    def execute(self, brand_id: int, buyer_person_id: int, base_image_id: str) -> dict:
        if not brand_id:
            logger.error("Brand id is required")
            raise ParametersNotFoundException('Brand Id is required')

        if not buyer_person_id:
            logger.error("Buyer Person id is required")
            raise ParametersNotFoundException('Buyer Person Id is required')

        if not base_image_id:
            logger.error("Base Image id is required")
            raise ParametersNotFoundException('Base Image Id is required')

        # Get Parent Account
        parent_account = self._get_parent_account()

        # Validate the Buyer Person belongs to this brand + account
        buyer_person = self.buyer_person_repository.get_by_id_and_brand_and_account(buyer_person_id=buyer_person_id, brand_id=brand_id, account_id=parent_account)
        if not buyer_person:
            logger.error(f"Buyer Person not found: {buyer_person_id} for brand {brand_id} and account {parent_account}")
            raise DataNotFoundException('Buyer Person not found for the given brand and account')

        # Validate the base (main) image exists for this buyer person
        buyer_main_image = self.buyer_main_image_repository.get_by_buyer_person_id_and_image_id(buyer_person_id, base_image_id)
        if not buyer_main_image:
            logger.error(f"Buyer Main Image not found for buyer person {buyer_person_id} and image id {base_image_id}")
            raise DataNotFoundException('Buyer Main Image not found for the given buyer person and image id')

        # List active variants of that base image
        variant_images = self.buyer_variant_image_repository.get_by_main_image_id(buyer_main_image.get('id'))

        # Resolve the presigned URL per variant image_id (same as the main-image flow)
        for image in variant_images:
            image_id = image.get('attributes', {}).get('image_id')
            try:
                if image_id:
                    image_url = self.image_library_repository.get_image(image_id)
                    image['attributes']['image_url'] = image_url.get('url') if image_url else None
                else:
                    logger.warning(f"Image ID not found for buyer variant image record: {image.get('id')}")
            except Exception as e:
                logger.error(f"Error getting image URL for variant image ID {image_id}: {e}")
                image['attributes']['image_url'] = None

        return self._build_response(buyer_person_id, base_image_id, variant_images)

class DeleteVariantImageUseCase(BuyerParsonBaseUseCase):
    """Soft-delete a single variant image of a base (main) image for a buyer person."""
    def __init__(self, user_id):
        super().__init__(user_id)
        self.buyer_main_image_repository = BuyerMainImageRepository()
        self.buyer_variant_image_repository = BuyerVariantImageRepository()

    def execute(self, brand_id: int, buyer_person_id: int, base_image_id: str, variant_id: int) -> dict:
        if not brand_id:
            logger.error("Brand id is required")
            raise ParametersNotFoundException('Brand Id is required')

        if not buyer_person_id:
            logger.error("Buyer Person id is required")
            raise ParametersNotFoundException('Buyer Person Id is required')

        if not base_image_id:
            logger.error("Base Image id is required")
            raise ParametersNotFoundException('Base Image Id is required')

        if not variant_id:
            logger.error("Variant id is required")
            raise ParametersNotFoundException('Variant Id is required')

        # Get Parent Account
        parent_account = self._get_parent_account()

        # Validate the Buyer Person belongs to this brand + account
        buyer_person = self.buyer_person_repository.get_by_id_and_brand_and_account(buyer_person_id=buyer_person_id, brand_id=brand_id, account_id=parent_account)
        if not buyer_person:
            logger.error(f"Buyer Person not found: {buyer_person_id} for brand {brand_id} and account {parent_account}")
            raise DataNotFoundException('Buyer Person not found for the given brand and account')

        # Validate the base (main) image exists for this buyer person
        buyer_main_image = self.buyer_main_image_repository.get_by_buyer_person_id_and_image_id(buyer_person_id, base_image_id)
        if not buyer_main_image:
            logger.error(f"Buyer Main Image not found for buyer person {buyer_person_id} and image id {base_image_id}")
            raise DataNotFoundException('Buyer Main Image not found for the given buyer person and image id')

        # Ownership check: the variant must belong to this base image
        variants = self.buyer_variant_image_repository.get_by_main_image_id(buyer_main_image.get('id'))
        variant = next((v for v in variants if str(v.get('id')) == str(variant_id)), None)
        if not variant:
            logger.error(f"Variant {variant_id} not found for base image {base_image_id} (buyer person {buyer_person_id})")
            raise DataNotFoundException('Variant image not found for the given base image')

        # Soft-delete the variant (status -> 'I')
        deleted = self.buyer_variant_image_repository.delete_by_id(variant_id)
        if not deleted:
            logger.error(f"Failed to soft delete variant image {variant_id}")
            raise SinergiaException('Failed to delete buyer variant image record')

        logger.debug(f"Buyer variant image {variant_id} marked as deleted for buyer person {buyer_person_id}")

        return {
            'id': int(variant_id),
            'image_id': variant.get('attributes', {}).get('image_id'),
            'label': variant.get('attributes', {}).get('label'),
            'status': 'I'
        }

class SelectVariantImageUseCase(BuyerParsonBaseUseCase):
    """Mark a variant image of a base (main) image as selected for a buyer person."""
    def __init__(self, user_id):
        super().__init__(user_id)
        self.buyer_main_image_repository = BuyerMainImageRepository()
        self.buyer_variant_image_repository = BuyerVariantImageRepository()

    def execute(self, brand_id: int, buyer_person_id: int, base_image_id: str, variant_id: str) -> dict:
        if not brand_id:
            logger.error("Brand id is required")
            raise ParametersNotFoundException('Brand Id is required')

        if not buyer_person_id:
            logger.error("Buyer Person id is required")
            raise ParametersNotFoundException('Buyer Person Id is required')

        if not base_image_id:
            logger.error("Base Image id is required")
            raise ParametersNotFoundException('Base Image Id is required')

        if not variant_id:
            logger.error("Variant id is required")
            raise ParametersNotFoundException('Variant Id is required')

        # Get Parent Account
        parent_account = self._get_parent_account()

        # Validate the Buyer Person belongs to this brand + account
        buyer_person = self.buyer_person_repository.get_by_id_and_brand_and_account(buyer_person_id=buyer_person_id, brand_id=brand_id, account_id=parent_account)
        if not buyer_person:
            logger.error(f"Buyer Person not found: {buyer_person_id} for brand {brand_id} and account {parent_account}")
            raise DataNotFoundException('Buyer Person not found for the given brand and account')

        # Validate the base (main) image exists for this buyer person
        buyer_main_image = self.buyer_main_image_repository.get_by_buyer_person_id_and_image_id(buyer_person_id, base_image_id)
        if not buyer_main_image:
            logger.error(f"Buyer Main Image not found for buyer person {buyer_person_id} and image id {base_image_id}")
            raise DataNotFoundException('Buyer Main Image not found for the given buyer person and image id')

        # Ownership check: the variant must belong to this base image
        variants = self.buyer_variant_image_repository.get_by_main_image_id(buyer_main_image.get('id'), status=['A', 'P'])
        variant = next((v for v in variants if str(v.get('attributes', {}).get('image_id', '')) == str(variant_id)), None)
        if not variant:
            logger.error(f"Variant {variant_id} not found for base image {base_image_id} (buyer person {buyer_person_id})")
            raise DataNotFoundException('Variant image not found for the given base image')

        # Mark the variant as selected
        selected = self.buyer_variant_image_repository.set_selected(variant.get('id'))
        if not selected:
            logger.error(f"Failed to select variant image {variant_id}")
            raise SinergiaException('Failed to select buyer variant image record')

        for v in variants:
            if v.get('attributes', {}).get('label') == variant.get('attributes', {}).get('label') and v.get('attributes', {}).get('status') == 'A' and v.get('attributes', {}).get('image_id') != variant_id:
                # Soft-delete the existing variant (status -> 'I')
                deleted = self.buyer_variant_image_repository.delete_by_id(v.get('id'))
                if not deleted:
                    logger.error(f"Failed to soft delete existing variant image {v.get('id')} with label {variant.get('attributes', {}).get('label')}")
                    # raise SinergiaException('Failed to delete existing buyer variant image record')
                logger.debug(f"Existing buyer variant image {v.get('id')} with label {variant.get('attributes', {}).get('label')} marked as deleted")

        logger.debug(f"Buyer variant image {variant_id} marked as selected for buyer person {buyer_person_id}")

        return {
            'id': variant.get('id'),
            'image_id': variant.get('attributes', {}).get('image_id'),
            'label': variant.get('attributes', {}).get('label'),
            'prompt': variant.get('attributes', {}).get('prompt', '')
        }

class GetAMainImageUseCase(BuyerParsonBaseUseCase):
    '''
    Fury Tools - Get a Main Image for a Buyer Person
    '''
    def __init__(self):
        super().__init__()
        self.buyer_main_image_repository = BuyerMainImageRepository()
        self.image_library_repository = ImageLibraryRepository()

    def execute(self, buyer_person_id: int, image_id: str) -> dict:
        if not buyer_person_id:
            logger.error("Buyer Person id is required")
            raise ParametersNotFoundException('Buyer Person Id is required')

        if not image_id:
            logger.error("Image id is required")
            raise ParametersNotFoundException('Image Id is required')

        image = self.buyer_main_image_repository.get_by_buyer_person_id_and_image_id(buyer_person_id, image_id)

        try:
            image_id = image.get('attributes', {}).get('image_id')
            if image_id:
                image_url = self.image_library_repository.get_image(image_id)
                image['attributes']['image_url'] = image_url.get('url') if image_url else None
            else:
                logger.warning(f"Image ID not found for buyer main image record: {image.get('id')}")
        except Exception as e:
            logger.error(f"Error getting image URL for image ID {image_id}: {e}")
            image['attributes']['image_url'] = None  # Set to None or some default value if URL retrieval fails

        response = {
            'id': image_id,
            'url': image.get('attributes', {}).get('image_url'),
            'prompt': image.get('attributes', {}).get('prompt')
        }

        return response
    
class EditMainImageUseCase(BuyerParsonBaseUseCase):
    def __init__(self, user_id):
        super().__init__(user_id)
        self.fury_client = FuryClient()
        self.product_repository = ProductRepository()

    def execute(self, payload: dict, save_as: str = 'main') -> dict:
        # Validate payload structure
        if not payload or not isinstance(payload, dict):
            raise IncorrectValidationException('Invalid payload')
        
        # Validar que el payload tenga los campos requeridos
        required_fields = ['brand_id', 'bperson_id', 'base_image_id', 'custom_prompt']

        for field in required_fields:
            if field not in payload:
                logger.error(f"Missing required field: {field}")
                raise IncorrectValidationException(f"Missing required field: {field}")
        
        brand_id = payload.get('brand_id')
        buyer_person_id = payload.get('bperson_id')
        base_image_id = payload.get('base_image_id')
        custom_prompt = payload.get('custom_prompt')
        n_variants = payload.get('n_variants', 4)  # Default to 4 variations if not provided
        photography_effect = payload.get('photography_effect')
        visual_style = payload.get('visual_style')
        product_id = payload.get('product_id')
        reference_images = payload.get('reference_images', [])  # Optional list of reference image URLs
        label = payload.get('label')
        label_key = ''

        if photography_effect:
            allowed_effects = ALLOWED_PHOTOGRAPHY_EFFECTS.keys()
            if photography_effect not in allowed_effects:
                logger.error(f"Invalid photography effect: {photography_effect}. Allowed values are: {', '.join(allowed_effects)}")
                raise IncorrectValidationException(f"The photography_effect field must be one of the following values: {', '.join(allowed_effects)}.")
            
            photography_effect = ALLOWED_PHOTOGRAPHY_EFFECTS.get(photography_effect)

        if visual_style:
            allowed_visual_styles = ALLOWED_VISUAL_STYLES.keys()
            if visual_style not in allowed_visual_styles:
                logger.error(f"Invalid visual style: {visual_style}. Allowed values are: {', '.join(allowed_visual_styles)}")
                raise IncorrectValidationException(f"The visual_style field must be one of the following values: {', '.join(allowed_visual_styles)}.")

            visual_style = ALLOWED_VISUAL_STYLES.get(visual_style)

        # Validar label
        if label:
            label_key = next((key for key in BUYER_IMAGE_VARIANT_LABELS.keys() if key.lower() == label.lower()), None)
            if not label_key:
                logger.error(f"Invalid label value: {label}. Allowed values are: {', '.join(BUYER_IMAGE_VARIANT_LABELS.keys())}")
                raise IncorrectValidationException(f"Invalid label value: {label}. Allowed values are: {', '.join(BUYER_IMAGE_VARIANT_LABELS.keys())}")

        # Get Parent Account
        parent_account = self._get_parent_account()
        
        # Buscar Buyer Person en la base de datos por id, brand_ref y account_ref
        buyer_person = self.buyer_person_repository.get_by_id_and_brand_and_account(buyer_person_id=buyer_person_id, brand_id=brand_id, account_id=parent_account)
        if not buyer_person:
            logger.error(f"Buyer Person not found: {buyer_person_id} for brand {brand_id} and account {parent_account}")
            raise DataNotFoundException('Buyer Person not found for the given brand and account')
        
        # Buscar Product en la base de datos por id, brand_ref y account_ref si product_id es proporcionado
        if product_id:
            product = self.product_repository.get_product_by_id_and_brand_and_account(product_id=product_id, brand_id=brand_id, account_id=parent_account)
            if not product:
                logger.error(f"Product not found: {product_id} for brand {brand_id} and account {parent_account}")
                raise DataNotFoundException('Product not found for the given brand and account')
            
        # Recorrer reference_images y convertir en base64 data URIs con el prefijo "data:{mime_type};base64,{data}"
        reference_image_data_uris = []
        for ref_image in reference_images:
            try:
                filename = ref_image.get('filename')
                content = ref_image.get('content')
                content_type = ref_image.get('content_type')

                if not filename or not content or not content_type:
                    logger.warning(f"Skipping invalid reference image: {ref_image}")
                    continue

                # Convertir a base64 data URI
                base64_data = b64encode(content).decode('utf-8')
                data_uri = f"data:{content_type};base64,{base64_data}"
                reference_image_data_uris.append(data_uri)
            except Exception as e:
                logger.error(f"Error processing reference image {ref_image}: {e}")
                continue
        

        try:
            if save_as == 'main':
                response = self.fury_client.post('/api/v2/persona-images/edit/main-image', 
                                                {'id_buyer_persona': buyer_person_id,
                                                'n_variations': n_variants,
                                                'photography_effect': photography_effect,
                                                'id_product': product_id,
                                                'custom_prompt': custom_prompt,
                                                'id_base_image': base_image_id,
                                                'reference_images': reference_image_data_uris if reference_image_data_uris else None,
                                                'visual_style': visual_style})

            else:
                response = self.fury_client.post('/api/v2/persona-images/edit/variant', 
                                                                {'id_buyer_persona': buyer_person_id,
                                                                'n_variations': n_variants,
                                                                'photography_effect': photography_effect,
                                                                'id_product': product_id,
                                                                'custom_prompt': custom_prompt,
                                                                'id_base_image': base_image_id,
                                                                'reference_images': reference_image_data_uris if reference_image_data_uris else None,
                                                                'label': label_key,
                                                                'visual_style': visual_style})
                
            return {'job_id': response.get('data', {}).get('task_id')}
        except Exception as e:
            logger.error(f"Error editing Buyer Person Main Image: {str(e)}")
            raise e

class DeleteMainImageUseCase(BuyerParsonBaseUseCase):
    def __init__(self, user_id):
        super().__init__(user_id)
        self.buyer_main_image_repository = BuyerMainImageRepository()
        self.buyer_variant_image_repository = BuyerVariantImageRepository()
        self.image_library_repository = ImageLibraryRepository()

    def execute(self, brand_id: int, buyer_person_id: int, image_id: str) -> dict:
        if not brand_id:
            logger.error("Brand id is required")
            raise ParametersNotFoundException('Brand Id is required')

        if not buyer_person_id:
            logger.error("Buyer Person id is required")
            raise ParametersNotFoundException('Buyer Person Id is required')

        if not image_id:
            logger.error("Image id is required")
            raise ParametersNotFoundException('Image Id is required')
        
        # Get Parent Account
        parent_account = self._get_parent_account()

        # Buscar Buyer Person en la base de datos por id, brand_ref y account_ref
        buyer_person = self.buyer_person_repository.get_by_id_and_brand_and_account(buyer_person_id=buyer_person_id, brand_id=brand_id, account_id=parent_account)
        if not buyer_person:
            logger.error(f"Buyer Person not found: {buyer_person_id} for brand {brand_id} and account {parent_account}")
            raise DataNotFoundException('Buyer Person not found for the given brand and account')

        # Validar que la imagen exista y obtener el image_library_id
        buyer_main_image = self.buyer_main_image_repository.get_by_id_and_buyer_person_id(image_id, buyer_person_id)
        if not buyer_main_image:
            logger.error(f"Buyer Main Image not found for buyer person {buyer_person_id} and image id {image_id}")
            raise DataNotFoundException('Buyer Main Image not found for the given buyer person and image id')
        
        # Eliminar el registro de la imagen principal del comprador
        try:
            deleted = self.buyer_main_image_repository.delete_by_id_and_buyer_person_id(image_id, buyer_person_id)

            if deleted:
                logger.debug(f"Buyer main image record with id {image_id} marked as deleted successfully for buyer person {buyer_person_id}")
                # Recorrer las variant_images asociadas a la imagen principal y eliminar las imágenes de Image Library
                variant_images = buyer_main_image.get('attributes', {}).get('variant_images', {}).get('data', [])
                print(variant_images)
                for variant_image in variant_images:
                    variant_image_id = variant_image.get('id')
                    if variant_image_id:
                        try:
                            self.buyer_variant_image_repository.delete_by_id(variant_image_id)
                        except Exception as e:
                            logger.error(f"Error deleting variant image {variant_image_id} from Image Library: {e}")
                            continue  # Continuar con la eliminación de las demás imágenes aunque falle alguna
            else:
                logger.error(f"Failed to mark buyer main image record with id {image_id} as deleted for buyer person {buyer_person_id}")
                raise SinergiaException('Failed to delete buyer main image record')

        except Exception as e:
            logger.error(f"Error deleting buyer main image record for buyer person {buyer_person_id} and image id {image_id}: {e}")
            raise e
        
        response = {
            'id': int(image_id),
            'image_id': buyer_main_image.get('attributes', {}).get('image_id'),
            'image_url': buyer_main_image.get('attributes', {}).get('image_url'),
            'prompt': buyer_main_image.get('attributes', {}).get('prompt'),
            'selected': False,
            'has_variants': False
        }
        
        return response
    
class GenerateVariantImagesUseCase(BuyerParsonBaseUseCase):
    def __init__(self, user_id):
        super().__init__(user_id)
        self.fury_client = FuryClient()
        self.buyer_main_image_repository = BuyerMainImageRepository()

    def execute(self, payload: dict) -> dict:
        # Validate payload structure
        if not payload or not isinstance(payload, dict):
            raise IncorrectValidationException('Invalid payload')
        
        # Validar que el payload tenga los campos requeridos
        required_fields = ['brand_id', 'bperson_id', 'image_id']

        for field in required_fields:
            if field not in payload:
                logger.error(f"Missing required field: {field}")
                raise IncorrectValidationException(f"Missing required field: {field}")
        
        brand_id = payload.get('brand_id')
        buyer_person_id = payload.get('bperson_id')
        image_id = payload.get('image_id')

        # Get Parent Account
        parent_account = self._get_parent_account()
        
        # Buscar Buyer Person en la base de datos por id, brand_ref y account_ref
        buyer_person = self.buyer_person_repository.get_by_id_and_brand_and_account(buyer_person_id=buyer_person_id, brand_id=brand_id, account_id=parent_account)
        if not buyer_person:
            logger.error(f"Buyer Person not found: {buyer_person_id} for brand {brand_id} and account {parent_account}")
            raise DataNotFoundException('Buyer Person not found for the given brand and account')
        
        # Buscar y validar que exista la imagen principal para la que se quieren generar las variantes
        buyer_main_image = self.buyer_main_image_repository.get_by_buyer_person_id_and_image_id(buyer_person_id, image_id)
        if not buyer_main_image:
            logger.error(f"Buyer Main Image not found for buyer person {buyer_person_id} and image id {image_id}")
            raise DataNotFoundException('Buyer Main Image not found for the given buyer person and image id')
        
        try:
            response = self.fury_client.post('/api/v2/persona-images/main-image/variant/generate', {'id_buyer_persona': int(buyer_person_id),
                                                                                                      'id_base_image': image_id,
                                                                                                      'id_product': None})
            return {'job_id': response.get('data', {}).get('task_id')}
        except Exception as e:
            logger.error(f"Error generating Buyer Person Main Image variants: {str(e)}")
            raise e
        
class UploadVariantImageBuyerPersonUseCase(UploadMainImageBuyerPersonUseCase):
    """Fury Tool: Use case for uploading variant images to a buyer person."""
    def __init__(self):
        super().__init__()
        self.buyer_variant_image_repository = BuyerVariantImageRepository()

    def execute(self, buyer_person_id: int, base_image_id: str, payload: dict) -> dict:
        """Upload a variant image for a buyer person.
        
        Args:
            buyer_person_id (int): ID of the buyer person
            base_image_id (str): UUID of the base main image
            payload (dict): Payload containing image: (image_data (base64), image_name, mime_type, image_prompt) and label: str
            
        Returns:
            dict: Created buyer main image record
        """
        try:
            logger.debug(f"Uploading variant image for buyer person: {buyer_person_id}")
            
            # Validate payload.image
            self._validate_payload(payload.get('image'))

            label = payload.get('label')
            label_key = ''

            # Validar label
            if label:
                label_key = next((key for key in BUYER_IMAGE_VARIANT_LABELS.keys() if key.lower() == label.lower()), None)
                if not label_key:
                    logger.error(f"Invalid label value: {label}. Allowed values are: {', '.join(BUYER_IMAGE_VARIANT_LABELS.keys())}")
                    raise IncorrectValidationException(f"Invalid label value: {label}. Allowed values are: {', '.join(BUYER_IMAGE_VARIANT_LABELS.keys())}")

            # Validate buyer person exists
            populate = ['brand_ref', 'account_ref.parent_account']
            buyer_person = self.buyer_person_repository.get_by_id(buyer_person_id, populate=populate)
            if not buyer_person:
                logger.error(f"Buyer Person not found: {buyer_person_id}")
                raise DataNotFoundException('Buyer Person not found')
            
            # Get parent account from buyer person
            account = buyer_person.get('attributes', {}).get('account_ref', {}).get('data', {})
            parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']
            if not parent_account:
                logger.error(f"Account not found for Buyer Person: {buyer_person_id}")
                raise DataNotFoundException('Account not found for Buyer Person')
            
            brand_id = buyer_person.get('attributes', {}).get('brand_ref', {}).get('data', {}).get('id')
            if not brand_id:
                logger.error(f"Brand not found for Buyer Person: {buyer_person_id}")
                raise DataNotFoundException('Brand not found for Buyer Person')
            
            # Buscar y validar que exista la imagen principal para la que se quieren generar las variantes
            buyer_variant_base_image = self.buyer_variant_image_repository.get_by_buyer_person_id_and_image_id(buyer_person_id, base_image_id, populate=['main_image_id'])
            if not buyer_variant_base_image:
                logger.error(f"Buyer Variant Base Image not found for buyer person {buyer_person_id} and image id {base_image_id}")
                raise DataNotFoundException('Buyer Variant Base not found for the given buyer person and image id')

            main_image_id = buyer_variant_base_image.get('attributes', {}).get('main_image_id', {}).get('data', {}).get('id')

            # Decodificar base64 a bytes
            try:
                image_data = payload.get('image', {}).get('image_data', '')
                # El valor puede venir con prefijo "data:{mime};base64,"
                if isinstance(image_data, str) and image_data.startswith('data:'):
                    comma_idx = image_data.find(',')
                    if comma_idx != -1:
                        image_data = image_data[comma_idx + 1:]

                image_bytes = b64decode(image_data)
            except Exception as e:
                logger.error(f"Invalid base64 image data: {e}")
                raise ParametersNotFoundException('Invalid base64 image data')

            # Crear buffer
            buffer = BytesIO(image_bytes)
            buffer.seek(0)

            # Subir imagen
            try:
                content_type = payload['image']['mime_type']
                filename = f"{payload['image']['image_name']}{self._get_extention_from_mime(content_type)}"
                params = { 'brand_id' : brand_id, 'buyer_id': buyer_person_id, 
                        'account_id': parent_account, 'category': 'buyer',
                        'type': 'original', 'subcategory': 'variant' }
            
                files = { 
                    'file' : (filename, buffer, content_type)#,
                }
                response = self.n8nClient.executePost('/webhook/v2/buyer_person/image/main/upload',{},False,is_binary=False,params=params,files=files)
                image_id = response.get('data', {}).get('image_id')
            except Exception as e:
                logger.error(f"Error uploading image: {e}")
                raise e
            
            # Create buyer variant image record
            buyer_variant_image_data = {
                'image_id': image_id,
                'label': label_key,
                'prompt': payload['image']['image_prompt'],
                'status': 'P',
                'main_image_id': main_image_id,
                'parent_image': buyer_variant_base_image.get('id')
            }
            
            created_image = self.buyer_variant_image_repository.create(buyer_variant_image_data)
            if not created_image:
                logger.error(f"Error creating buyer variant image record")
                raise SinergiaException('Error creating buyer variant image record')
            
            logger.debug(f"Buyer variant image created successfully: {created_image.get('id')}")

            return {'image_id': created_image.get('attributes', {}).get('image_id', '')}
            
        except SinergiaException as e:
            logger.error(f"Error uploading buyer person mavariantin image: {e.text}")
            raise e
        except ImageLibraryException as e:
            logger.error(f"Error uploading buyer person variant image: {e}")
            raise e
        except Exception as err:
            logger.error(f"Error uploading buyer person variant image: {err}")
            raise SinergiaException('Error uploading buyer person variant image')

class UploadVariantImageByIdUseCase(BuyerParsonBaseUseCase):
    """Use case for uploading variant images to a buyer person by image_id."""
    def __init__(self, user_id):
        super().__init__(user_id)
        self.buyer_variant_image_repository = BuyerVariantImageRepository()
        self.image_library_repository = ImageLibraryRepository()
        self.buyer_main_image_repository = BuyerMainImageRepository()

    def _validate_payload(self, payload: dict) -> None:
        """Validate the payload structure and types."""
        if not payload or not isinstance(payload, dict):
            logger.error(f"Invalid payload: {payload}")
            raise IncorrectValidationException('Invalid payload')
        
        # Validar que el payload tenga los campos requeridos
        required_fields = ['brand_id', 'bperson_id', 'image_id', 'main_image_id']

        for field in required_fields:
            if field not in payload:
                logger.error(f"Missing required field: {field}")
                raise IncorrectValidationException(f"Missing required field: {field}")
            
        # Validate brand_id field type int
        if not isinstance(payload.get('brand_id'), int):
            logger.error(f"Invalid type for brand_id: {type(payload.get('brand_id'))}. Expected int.")
            raise IncorrectValidationException('Invalid type for brand_id. Expected int.')
        
        # Validate bperson_id field type int
        if not isinstance(payload.get('bperson_id'), int):
            logger.error(f"Invalid type for bperson_id: {type(payload.get('bperson_id'))}. Expected int.")
            raise IncorrectValidationException('Invalid type for bperson_id. Expected int.')
        
        # Validate image_id field type str
        if not isinstance(payload.get('image_id'), str):
            logger.error(f"Invalid type for image_id: {type(payload.get('image_id'))}. Expected str.")
            raise IncorrectValidationException('Invalid type for image_id. Expected str.')
        
        # Validate label field type str
        if payload.get('label') and not isinstance(payload.get('label'), str):
            logger.error(f"Invalid type for label: {type(payload.get('label'))}. Expected str.")
            raise IncorrectValidationException('Invalid type for label. Expected str.')
        
        # Validate main_image_id field type str
        if not isinstance(payload.get('main_image_id'), str):
            logger.error(f"Invalid type for main_image_id: {type(payload.get('main_image_id'))}. Expected str.")
            raise IncorrectValidationException('Invalid type for main_image_id. Expected str.')
        
    def execute(self, payload: dict) -> dict:
        """Upload a variant image for a buyer person by image_id.
        
        Args:
            payload (dict): Payload containing brand_id, bperson_id, image_id, label and main_image_id

        Returns:
            dict: Created buyer variant image record
        """
        try:
            logger.debug(f"Uploading variant image by image_id for buyer person")
            
            # Validate payload
            self._validate_payload(payload)

            brand_id = payload.get('brand_id')
            buyer_person_id = payload.get('bperson_id')
            image_id = payload.get('image_id')
            label = payload.get('label')
            main_image_id = payload.get('main_image_id')
            label_key = ''

            # Validar label
            if label:
                label_key = next((key for key in BUYER_IMAGE_VARIANT_LABELS.keys() if key.lower() == label.lower()), None)
                if not label_key:
                    logger.error(f"Invalid label value: {label}. Allowed values are: {', '.join(BUYER_IMAGE_VARIANT_LABELS.keys())}")
                    raise IncorrectValidationException(f"Invalid label value: {label}. Allowed values are: {', '.join(BUYER_IMAGE_VARIANT_LABELS.keys())}")

            # Get Parent Account
            parent_account = self._get_parent_account()
            
            # Buscar Buyer Person en la base de datos por id, brand_ref y account_ref
            buyer_person = self.buyer_person_repository.get_by_id_and_brand_and_account(buyer_person_id=buyer_person_id, brand_id=brand_id, account_id=parent_account)
            if not buyer_person:
                logger.error(f"Buyer Person not found: {buyer_person_id} for brand {brand_id} and account {parent_account}")
                raise DataNotFoundException('Buyer Person not found for the given brand and account')
            
            # Buscar y validar que exista la imagen principal para la que se quieren guardar la variante
            buyer_main_image = self.buyer_main_image_repository.get_by_buyer_person_id_and_image_id(buyer_person_id, main_image_id, populate=['variant_images'])
            if not buyer_main_image:
                logger.error(f"Buyer Main Image not found for buyer person {buyer_person_id} and image id {main_image_id}")
                raise DataNotFoundException('Buyer Main Image not found for the given buyer person and image id')
            
            # Si image_id ya existe en buyer_main_image.attributes.variant_images con status == 'A' y label == label_key, lanzar error de validación
            existing_variants = buyer_main_image.get('attributes', {}).get('variant_images', {}).get('data', [])
            for variant in existing_variants:
                if variant.get('attributes', {}).get('image_id') == image_id and variant.get('attributes', {}).get('label') == label_key and variant.get('attributes', {}).get('status') == 'A':
                    logger.error(f"Variant image with image_id {image_id} and label {label_key} already exists for buyer person {buyer_person_id}")
                    raise IncorrectValidationException(f"Variant image with image_id {image_id} and label {label_key} already exists for this buyer person")
            
            # Validar que la imagen exista en Image Library
            image_record = self.image_library_repository.get_image(image_id)
            if not image_record or 'error' in image_record or 'imageId' not in image_record:
                logger.error(f"Image not found in Image Library: {image_id}. Response: {image_record}")
                raise DataNotFoundException('Image not found in Image Library')
            
            # Create buyer variant image record
            buyer_variant_image_data = {
                'image_id': image_id,
                'label': label_key,
                'prompt': '',
                'status': 'A',
                'main_image_id': buyer_main_image.get('id'),
            }

            created_image = self.buyer_variant_image_repository.create(buyer_variant_image_data)
            if not created_image:
                logger.error(f"Error creating buyer variant image record")
                raise SinergiaException('Error creating buyer variant image record')
            
            logger.debug(f"Buyer variant image created successfully: {created_image.get('id')}")

            # Recorrer buyer_main_image.attributes.variant_images y actualizar la imagen a status = 'I' si es que ya existe una variante con el mismo label y status == 'A'
            existing_variants = buyer_main_image.get('attributes', {}).get('variant_images', {}).get('data', [])
            for variant in existing_variants:
                if variant.get('attributes', {}).get('label') == label_key and variant.get('attributes', {}).get('status') == 'A':
                    # Soft-delete the existing variant (status -> 'I')
                    deleted = self.buyer_variant_image_repository.delete_by_id(variant.get('id'))
                    if not deleted:
                        logger.error(f"Failed to soft delete existing variant image {variant.get('id')} with label {label_key}")
                        # raise SinergiaException('Failed to delete existing buyer variant image record')
                    logger.debug(f"Existing buyer variant image {variant.get('id')} with label {label_key} marked as deleted")

            return {
                'id': int(created_image.get('id')),
                'image_id': created_image.get('attributes', {}).get('image_id', ''),
                'image_url': image_record.get('url', ''),
                'label': created_image.get('attributes', {}).get('label', ''),
                'status': created_image.get('attributes', {}).get('status', 'A'),
                'prompt': created_image.get('attributes', {}).get('prompt', '')
            }
        
        except SinergiaException as e:
            logger.error(f"Error uploading buyer person variant image by image_id: {e.text}")
            raise e
        except ImageLibraryException as e:
            logger.error(f"Error uploading buyer person variant image by image_id: {e}")
            raise e
        except Exception as err:
            logger.error(f"Error uploading buyer person variant image by image_id: {err}")
            raise SinergiaException('Error uploading buyer person variant image by image_id')
        
class UploadVariantImageBinarydUseCase(BuyerParsonBaseUseCase):
    """Use case for uploading variant images to a buyer person by binary data."""
    def __init__(self, user_id):
        super().__init__(user_id)
        self.buyer_variant_image_repository = BuyerVariantImageRepository()
        self.image_library_repository = ImageLibraryRepository()
        self.buyer_main_image_repository = BuyerMainImageRepository()
        self.n8nClient = N8NClient()

    def _validate_payload(self, payload: dict) -> None:
        """Validate the payload structure and types."""
        if not payload or not isinstance(payload, dict):
            logger.error(f"Invalid payload: {payload}")
            raise IncorrectValidationException('Invalid payload')
        
        # Validar que el payload tenga los campos requeridos
        required_fields = ['brand_id', 'bperson_id', 'main_image_id', 'image']

        for field in required_fields:
            if field not in payload:
                logger.error(f"Missing required field: {field}")
                raise IncorrectValidationException(f"Missing required field: {field}")
            
        # Validate brand_id field type int
        if not isinstance(payload.get('brand_id'), int):
            logger.error(f"Invalid type for brand_id: {type(payload.get('brand_id'))}. Expected int.")
            raise IncorrectValidationException('Invalid type for brand_id. Expected int.')
        
        # Validate bperson_id field type int
        if not isinstance(payload.get('bperson_id'), int):
            logger.error(f"Invalid type for bperson_id: {type(payload.get('bperson_id'))}. Expected int.")
            raise IncorrectValidationException('Invalid type for bperson_id. Expected int.')
        
        # Validate label field type str
        if payload.get('label') and not isinstance(payload.get('label'), str):
            logger.error(f"Invalid type for label: {type(payload.get('label'))}. Expected str.")
            raise IncorrectValidationException('Invalid type for label. Expected str.')
        
        # Validate main_image_id field type str
        if not isinstance(payload.get('main_image_id'), str):
            logger.error(f"Invalid type for main_image_id: {type(payload.get('main_image_id'))}. Expected str.")
            raise IncorrectValidationException('Invalid type for main_image_id. Expected str.')
        
        # Validate image field type dict
        if not isinstance(payload.get('image'), dict):
            logger.error(f"Invalid type for image: {type(payload.get('image'))}. Expected dict.")
            raise IncorrectValidationException('Invalid type for image. Expected dict.')
        
    def execute(self, payload: dict) -> dict:
        """Upload a variant image for a buyer person by binary data.
        
        Args:
            payload (dict): Payload containing brand_id, bperson_id, label, main_image_id and image (with keys: filename, content, content_type)

        Returns:
            dict: Created buyer variant image record
        """
        try:
            logger.debug(f"Uploading variant image by binary data for buyer person")
            
            # Validate payload
            self._validate_payload(payload)

            brand_id = payload.get('brand_id')
            buyer_person_id = payload.get('bperson_id')
            label = payload.get('label')
            main_image_id = payload.get('main_image_id')
            image_info = payload.get('image')
            label_key = ''

            # Validar label
            if label:
                label_key = next((key for key in BUYER_IMAGE_VARIANT_LABELS.keys() if key.lower() == label.lower()), None)
                if not label_key:
                    logger.error(f"Invalid label value: {label}. Allowed values are: {', '.join(BUYER_IMAGE_VARIANT_LABELS.keys())}")
                    raise IncorrectValidationException(f"Invalid label value: {label}. Allowed values are: {', '.join(BUYER_IMAGE_VARIANT_LABELS.keys())}")

            # Get Parent Account
            parent_account = self._get_parent_account()
            
            # Buscar Buyer Person en la base de datos por id, brand_ref y account_ref
            buyer_person = self.buyer_person_repository.get_by_id_and_brand_and_account(buyer_person_id=buyer_person_id, brand_id=brand_id, account_id=parent_account)
            if not buyer_person:
                logger.error(f"Buyer Person not found: {buyer_person_id} for brand {brand_id} and account {parent_account}")
                raise DataNotFoundException('Buyer Person not found for the given brand and account')
            
            # Buscar y validar que exista la imagen principal para la que se quieren guardar la variante
            buyer_main_image = self.buyer_main_image_repository.get_by_buyer_person_id_and_image_id(buyer_person_id, main_image_id, populate=['variant_images'])
            if not buyer_main_image:
                logger.error(f"Buyer Main Image not found for buyer person {buyer_person_id} and image id {main_image_id}")
                raise DataNotFoundException('Buyer Main Image not found for the given buyer person and image id')
            
            # Validar que la imagen tenga los campos requeridos
            required_image_fields = ['filename', 'content', 'content_type']
            for field in required_image_fields:
                if field not in image_info:
                    logger.error(f"Missing required field in image: {field}")
                    raise IncorrectValidationException(f"Missing required field in image: {field}")
                
            # Subir imagen utilizando el cliente n8nClient
            try:
                content_type = image_info['content_type']
                filename = image_info['filename']
                content = image_info['content']

                # Crear buffer
                buffer = BytesIO(content)
                buffer.seek(0)

                params = { 'brand_id' : brand_id, 'buyer_id': buyer_person_id, 
                        'account_id': parent_account, 'category': 'buyer',
                        'type': 'original', 'subcategory': 'variant' }
            
                files = { 
                    'file' : (filename, buffer, content_type)
                }
                response = self.n8nClient.executePost('/webhook/v2/buyer_person/image/main/upload',{},False,is_binary=False,params=params,files=files)
                image_id = response.get('data', {}).get('image_id')
            except Exception as e:
                logger.error(f"Error uploading image: {e}")
                raise e
            
            # Create buyer variant image record
            buyer_variant_image_data = {
                'image_id': image_id,
                'label': label_key,
                'prompt': '',
                'status': 'A',
                'main_image_id': buyer_main_image.get('id'),
            }

            created_image = self.buyer_variant_image_repository.create(buyer_variant_image_data)
            if not created_image:
                logger.error(f"Error creating buyer variant image record")
                raise SinergiaException('Error creating buyer variant image record')
            
            logger.debug(f"Buyer variant image created successfully: {created_image.get('id')}")

            # Recorrer buyer_main_image.attributes.variant_images y actualizar la imagen a status = 'I' si es que ya existe una variante con el mismo label y status == 'A'
            existing_variants = buyer_main_image.get('attributes', {}).get('variant_images', {}).get('data', [])
            for variant in existing_variants:
                if variant.get('attributes', {}).get('label') == label_key and variant.get('attributes', {}).get('status') == 'A':
                    # Soft-delete the existing variant (status -> 'I')
                    deleted = self.buyer_variant_image_repository.delete_by_id(variant.get('id'))
                    if not deleted:
                        logger.error(f"Failed to soft delete existing variant image {variant.get('id')} with label {label_key}")
                        raise SinergiaException('Failed to delete existing buyer variant image record')
                    logger.debug(f"Existing buyer variant image {variant.get('id')} with label {label_key} marked as deleted")

            # Esperar 12s y consultar la imagen en Image Library para obtener la URL
            time.sleep(12)
            image_record = self.image_library_repository.get_image(image_id)
            image_url = image_record.get('url', '') if image_record else ''

            return {
                'id': int(created_image.get('id')),
                'image_id': created_image.get('attributes', {}).get('image_id', ''),
                'image_url': image_url,
                'label': created_image.get('attributes', {}).get('label', ''),
                'status': created_image.get('attributes', {}).get('status', 'A'),
                'prompt': created_image.get('attributes', {}).get('prompt', '')
            }
        
        except SinergiaException as e:
            logger.error(f"Error uploading buyer person variant image by binary data: {e.text}")
            raise e
        except ImageLibraryException as e:
            logger.error(f"Error uploading buyer person variant image by binary data: {e}")
            raise e
        except Exception as err:
            logger.error(f"Error uploading buyer person variant image by binary data: {err}")
            raise SinergiaException('Error uploading buyer person variant image by binary data')

class GetAVariantImageFuryToolUseCase(BuyerParsonBaseUseCase):
    '''
    Fury Tools - Get a Variant Image for a Buyer Person
    '''
    def __init__(self):
        super().__init__()
        self.buyer_variant_image_repository = BuyerVariantImageRepository()
        self.image_library_repository = ImageLibraryRepository()

    def execute(self, buyer_person_id: int, image_id: str) -> dict:
        if not buyer_person_id:
            logger.error("Buyer Person id is required")
            raise ParametersNotFoundException('Buyer Person Id is required')

        if not image_id:
            logger.error("Image id is required")
            raise ParametersNotFoundException('Image Id is required')

        image = self.buyer_variant_image_repository.get_by_buyer_person_id_and_image_id(buyer_person_id, image_id)

        try:
            image_id = image.get('attributes', {}).get('image_id')
            if image_id:
                image_url = self.image_library_repository.get_image(image_id)
                image['attributes']['image_url'] = image_url.get('url') if image_url else None
            else:
                logger.warning(f"Image ID not found for buyer main image record: {image.get('id')}")
        except Exception as e:
            logger.error(f"Error getting image URL for image ID {image_id}: {e}")
            image['attributes']['image_url'] = None  # Set to None or some default value if URL retrieval fails

        response = {
            'id': image_id,
            'url': image.get('attributes', {}).get('image_url'),
            'prompt': image.get('attributes', {}).get('prompt')
        }

        return response

class GetAVariantImageUseCase(BuyerParsonBaseUseCase):
    """Get a buyer variant image for a buyer person and enrich it with Image Library URLs."""

    def __init__(self, user_id=None):
        super().__init__(user_id)
        self.buyer_variant_image_repository = BuyerVariantImageRepository()
        self.image_library_repository = ImageLibraryRepository()

    def _resolve_image_url(self, image_id: str) -> str:
        """Resolve an Image Library URL for a given image id."""
        if not image_id:
            return None

        try:
            image_record = self.image_library_repository.get_image(image_id)
            if not image_record:
                logger.warning(f"Image record not found in Image Library for image_id {image_id}")
                return None
            return image_record.get('url')
        except Exception as e:
            logger.error(f"Error getting image URL for image ID {image_id}: {e}")
            return None

    def execute(self, brand_id: int, buyer_person_id: int, image_id: str) -> dict:
        """Return a buyer variant image record with its own URL and all associated variant images URLs."""
        if not brand_id:
            logger.error("Brand id is required")
            raise ParametersNotFoundException('Brand Id is required')

        if not buyer_person_id:
            logger.error("Buyer Person id is required")
            raise ParametersNotFoundException('Buyer Person Id is required')

        if not image_id:
            logger.error("Image id is required")
            raise ParametersNotFoundException('Image Id is required')

        parent_account = self._get_parent_account()
        buyer_person = self.buyer_person_repository.get_by_id_and_brand_and_account(
            buyer_person_id=buyer_person_id,
            brand_id=brand_id,
            account_id=parent_account
        )

        if not buyer_person:
            logger.error(f"Buyer Person not found: {buyer_person_id} for brand {brand_id} and account {parent_account}")
            raise DataNotFoundException('Buyer Person not found for the given brand and account')

        buyer_variant_image = self.buyer_variant_image_repository.get_by_buyer_person_id_and_image_id(
            buyer_person_id=buyer_person_id,
            image_id=image_id,
            populate=['variant_images']
        )

        if not buyer_variant_image:
            logger.error(f"Buyer Variant Image not found for buyer person {buyer_person_id} and image id {image_id}")
            raise DataNotFoundException('Buyer Variant Image not found for the given buyer person and image id')

        attributes = buyer_variant_image.get('attributes', {})
        image_library_image_id = attributes.get('image_id')
        image_url = self._resolve_image_url(image_library_image_id)

        variant_images = []
        related_variant_images = attributes.get('variant_images', {}).get('data', []) or []
        for variant_image in related_variant_images:
            variant_attributes = variant_image.get('attributes', {}) or {}
            variant_image_id = variant_attributes.get('image_id')
            variant_image_url = self._resolve_image_url(variant_image_id)

            variant_images.append({
                'id': variant_image.get('id'),
                'image_id': variant_image_id,
                'image_url': variant_image_url,
                'label': variant_attributes.get('label'),
                # 'status': variant_attributes.get('status'),
                'prompt': variant_attributes.get('prompt', '')
            })

        response = {
            'id': buyer_variant_image.get('id'),
            'image_id': image_library_image_id,
            'image_url': image_url,
            'label': attributes.get('label'),
            # 'status': attributes.get('status'),
            'prompt': attributes.get('prompt', ''),
            'images': variant_images
        }

        return response