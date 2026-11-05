import logging
import base64
import mimetypes
from io import BytesIO
from typing import Any, Dict
from app.v2.repository.product import ProductRepository
from app.v2.repository.product_image import ProductImageRepository
from app.v2.repository.image_library import ImageLibraryRepository
from app.v2.repository.ad import AdRepository
from app.v2.repository.campaign import CampaignRepository
from app.v2.repository.ad_channel import AdChannelRepository
from app.exceptions.base import DataNotFoundException, ParametersNotFoundException
from app.v1.repository.base import N8NClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _is_invalid_param(value: Any) -> bool:
    """Invalid_Param: None, '', solo espacios en blanco o el entero 0. '0' es válido."""
    if not value:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _is_existing_image(record: Any) -> bool:
    """Existing_Image: dict no vacío con 'url' de tipo str no vacía ni solo espacios."""
    if not isinstance(record, dict) or not record:
        return False
    url = record.get('url')
    return isinstance(url, str) and bool(url.strip())


def _extract_prompt(record: Dict[str, Any]) -> str:
    """image_prompt si es str (incluida ''); en otro caso ''."""
    prompt = record.get('image_prompt')
    return prompt if isinstance(prompt, str) else ''


class GetProductImagesUseCase():
    def __init__(self):
        self.product_repository = ProductRepository()
        self.product_image_repository = ProductImageRepository()
        self.image_library_repository = ImageLibraryRepository()

    def execute(self, product_id):
        if not product_id:
            logger.error("Product Id is required")
            raise ParametersNotFoundException('Product Id is required')

        product = self.product_repository.get_by_id(product_id)
        if not product:
            logger.error(f"Product not found for id: {product_id}")
            raise DataNotFoundException('Product not found')

        product_images = self.product_image_repository.get_by_product_id(product_id)
        if not product_images:
            logger.info(f"No product images found for product id: {product_id}")
            return []

        image_urls = []
        for product_image in product_images:
            image_id = product_image.get('attributes', {}).get('image_id')
            if not image_id:
                continue
            image = self.image_library_repository.get_image(image_id)
            if image and image.get('url'):
                image_urls.append({'url': image.get('url')})

        return image_urls

class UploadImageFuryUseCase():
    def __init__(self):
        self.image_library_repository = ImageLibraryRepository()
        self.ad_repository = AdRepository()
        self.n8nClient = N8NClient()

    def _get_extention_from_mime(self, mime_type):
        ext = mimetypes.guess_extension(mime_type)
        if not ext:
            ext = '.jpg'  # Default to .jpg if MIME type is unknown
        return ext

    def execute(self, id_ad, payload):
        if not id_ad:
            logger.error("Ad ID is required")
            raise ParametersNotFoundException('Ad ID is required')
        
        if not payload or not isinstance(payload, dict):
            logger.error("Payload is required and must be a dict")
            raise ParametersNotFoundException('Payload is required and must be a dict')
        
        required_keys = ['image_data', 'image_name', 'mime_type']
        for key in required_keys:
            if key not in payload.get('image', {}):
                logger.error(f"Missing required key: {key}")
                raise ParametersNotFoundException(f"Missing required key: {key}")

        # Buscar ad por id
        populate = ['ad_set_ref2.funnel_flow_ref.campaign_ref.brand_ref','ad_set_ref2.funnel_flow_ref.campaign_ref.account_ref.parent_account']
        ad = self.ad_repository.get_by_id(id_ad, populate)
        if not ad:
            logger.error(f"Ad not found for id: {id_ad}")
            raise DataNotFoundException('Ad not found')

        # Extraer brand_id
        try:
            brand_id = ad['attributes']['ad_set_ref2']['data']['attributes']['funnel_flow_ref']['data']['attributes']['campaign_ref']['data']['attributes']['brand_ref']['data']['id']
        except (KeyError, TypeError):
            logger.error(f"Brand not found for ad: {id_ad}")
            raise DataNotFoundException('Brand not found for ad')

        # Extraer parent_account
        try:
            account = ad['attributes']['ad_set_ref2']['data']['attributes']['funnel_flow_ref']['data']['attributes']['campaign_ref']['data']['attributes']['account_ref']['data']
            parent_account = account['attributes']['parent_account']['data']['id'] if account.get('attributes', {}).get('parent_account', {}).get('data') else account['id']
        except (KeyError, TypeError):
            logger.error(f"Account not found for ad: {id_ad}")
            raise DataNotFoundException('Account not found for ad')

        # Decodificar base64 a bytes
        try:
            image_data = payload.get('image').get('image_data', '')
            # El valor puede venir con prefijo "data:{mime};base64,"
            if isinstance(image_data, str) and image_data.startswith('data:'):
                comma_idx = image_data.find(',')
                if comma_idx != -1:
                    image_data = image_data[comma_idx + 1:]

            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            logger.error(f"Invalid base64 image data: {e}")
            raise ParametersNotFoundException('Invalid base64 image data')

        # Crear buffer
        buffer = BytesIO(image_bytes)
        buffer.seek(0)

        # Construir metadata y body
        metadata = {
            'category': 'ads',
            'description': f"{ad['attributes']['name']} - {payload['image']['image_name']}",
            'type': 'original',
            'ad': id_ad,
            'brand': brand_id
        }
        body = {
            'accountId': parent_account,
            'fileName': f"{payload['image']['image_name']}",
            'contentType': payload['image']['mime_type'],
            'metadata': metadata
        }

        # Subir imagen
        try:
            content_type = payload['image']['mime_type']
            filename = f"{payload['image']['image_name']}{self._get_extention_from_mime(content_type)}"
            image_prompt = payload['image'].get('image_prompt', '') or ''
            params = { 'brand_id' : brand_id, 'ad_id': id_ad, 
                      'account_id': parent_account, 'category': 'ads',
                      'type': 'original', 'image_prompt': image_prompt }
         
            files = { 
                'file' : (filename, buffer, content_type)#,
            }
            response = self.n8nClient.executePost('/webhook/v2/ad/variant/image/upload',{},False,is_binary=False,params=params,files=files)
            image_id = response.get('data', {}).get('image_id')
            # image_id = self.image_library_repository.upload_image(buffer, body)
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            raise e

        return {'image_id': image_id}


class GetAdVariantImageUseCase():
    def __init__(self):
        self.campaign_repository = CampaignRepository()
        self.ad_channel_repository = AdChannelRepository()
        self.image_library_repository = ImageLibraryRepository()

    def execute(self, brand_id: int, campaign_id: int, ad_id: int,
                channel_id: int, variant_id: int, image_id: str) -> Dict[str, str]:
        # Validación en orden fijo: se lanza en el primer parámetro inválido
        required = (
            (brand_id, 'Brand Id is required'),
            (campaign_id, 'Campaign Id is required'),
            (ad_id, 'Ad Id is required'),
            (channel_id, 'Channel Id is required'),
            (variant_id, 'Variant Id is required'),
            (image_id, 'Image Id is required'),
        )
        for value, message in required:
            if _is_invalid_param(value):
                logger.error(message)
                raise ParametersNotFoundException(message)

        # La campaña debe pertenecer a la marca
        campaign = self.campaign_repository.get_by_id_and_brand(campaign_id, brand_id)
        if campaign is None:
            logger.error(f"Campaign not found for brand: campaign_id={campaign_id} brand_id={brand_id}")
            raise DataNotFoundException('Campaign not found for brand')

        # La variante (ad-channel) debe pertenecer al anuncio, campaña y canal
        ad_channel = self.ad_channel_repository.get_by_id_ad_campaign_and_channel(
            variant_id, ad_id, campaign_id, channel_id)
        if ad_channel is None:
            logger.error(
                f"Ad variant not found: variant_id={variant_id} ad_id={ad_id} "
                f"campaign_id={campaign_id} channel_id={channel_id}")
            raise DataNotFoundException('Ad variant not found')

        # Solo se valida la existencia de la imagen
        image = self.image_library_repository.get_image(image_id)
        if not _is_existing_image(image):
            logger.error(f"Image not found: image_id={image_id}")
            raise DataNotFoundException('Image not found')

        return {
            'id': image_id,
            'url': image['url'],
            'prompt': _extract_prompt(image),
        }
