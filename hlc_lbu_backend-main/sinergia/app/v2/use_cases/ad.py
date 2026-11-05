import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.v2.repository.account import AccountRepository
from app.v2.repository.campaign import CampaignRepository
from app.v2.repository.ad_channel import AdChannelRepository
from app.v2.repository.brand import BrandRepository
from app.v2.repository.ad import AdRepository
from app.v2.repository.abyssale_visual_ad_channel import AbyssaleVisualAdChannelRepository
from app.exceptions.base import (DataNotFoundException, ParametersNotFoundException,
                                 IncorrectValidationException, FuryException, SinergiaException)
from app.tools.fury import FuryClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Edit Ad Variant Image: constants ---
EDIT_IMAGE_FURY_ENDPOINT = '/api/v2/variants/image/edit'
EDIT_IMAGE_ID_FIELDS = ('brand_id', 'campaign_id', 'ad_id', 'channel_id', 'variant_id')
EDIT_IMAGE_STRING_FIELDS = ('image_name', 'image_id')
EDIT_IMAGE_REQUIRED_FIELDS = EDIT_IMAGE_ID_FIELDS + EDIT_IMAGE_STRING_FIELDS + ('n_variations',)
EDIT_IMAGE_EXPAND_ZOOM_OPTIONS = ('TOP', 'BOTTOM', 'LEFT', 'RIGHT', 'ZOOM_2X', 'ZOOM_1_5X', 'ZOOM_1_25X')
EDIT_IMAGE_MIN_ID = 1
EDIT_IMAGE_MIN_VARIATIONS = 1
EDIT_IMAGE_MAX_VARIATIONS = 10
EDIT_IMAGE_MAX_STRING_LENGTH = 255
EDIT_IMAGE_MAX_PROMPT_LENGTH = 2000


# --- Edit Ad Variant Image: private helpers ---
def _edit_image_fail(exc: SinergiaException) -> SinergiaException:
    """Log the exception text once with logger.error and return it so the caller can `raise` it."""
    logger.error(exc.text)
    return exc


def _edit_image_is_missing(value: Any) -> bool:
    """Missing_Value: None or a str that is empty/whitespace after strip(). Absent keys arrive as None."""
    if value is None:
        return True
    return isinstance(value, str) and value.strip() == ''


def _edit_image_is_valid_int(value: Any) -> bool:
    """Valid_Integer: an int that is not a bool."""
    return isinstance(value, int) and not isinstance(value, bool)


def _edit_image_normalize_prompt(value: Any) -> Optional[str]:
    """Normalized_Custom_Prompt: stripped str, or None if None/empty after strip. Called only with None or str."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _edit_image_check_presence(payload: Any) -> None:
    """Req 3: payload must be a dict and every Required_Field must be present (first missing one wins)."""
    if not isinstance(payload, dict):
        raise _edit_image_fail(ParametersNotFoundException('Payload is required'))
    for field in EDIT_IMAGE_REQUIRED_FIELDS:
        if _edit_image_is_missing(payload.get(field)):
            raise _edit_image_fail(ParametersNotFoundException(f'{field} is required'))


def _edit_image_validate(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Req 4: validate values in the order of Req 4.7 and return the normalized values (D5)."""
    for field in EDIT_IMAGE_ID_FIELDS:
        value = payload.get(field)
        if not _edit_image_is_valid_int(value) or value < EDIT_IMAGE_MIN_ID:
            raise _edit_image_fail(IncorrectValidationException(
                f'{field} must be an integer greater than or equal to {EDIT_IMAGE_MIN_ID}'))

    for field in EDIT_IMAGE_STRING_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or len(value.strip()) > EDIT_IMAGE_MAX_STRING_LENGTH:
            raise _edit_image_fail(IncorrectValidationException(
                f'{field} must be a string of at most {EDIT_IMAGE_MAX_STRING_LENGTH} characters'))

    n_variations = payload.get('n_variations')
    if (not _edit_image_is_valid_int(n_variations)
            or n_variations < EDIT_IMAGE_MIN_VARIATIONS
            or n_variations > EDIT_IMAGE_MAX_VARIATIONS):
        raise _edit_image_fail(IncorrectValidationException(
            f'n_variations must be an integer between {EDIT_IMAGE_MIN_VARIATIONS} and {EDIT_IMAGE_MAX_VARIATIONS}'))

    prompt_error = f'custom_prompt must be a string of at most {EDIT_IMAGE_MAX_PROMPT_LENGTH} characters'
    raw_prompt = payload.get('custom_prompt')
    if raw_prompt is not None and not isinstance(raw_prompt, str):
        raise _edit_image_fail(IncorrectValidationException(prompt_error))
    custom_prompt = _edit_image_normalize_prompt(raw_prompt)
    if custom_prompt is not None and len(custom_prompt) > EDIT_IMAGE_MAX_PROMPT_LENGTH:
        raise _edit_image_fail(IncorrectValidationException(prompt_error))

    expand_zoom_option = payload.get('expand_zoom_option')
    if expand_zoom_option is not None and not (
            isinstance(expand_zoom_option, str) and expand_zoom_option in EDIT_IMAGE_EXPAND_ZOOM_OPTIONS):
        raise _edit_image_fail(IncorrectValidationException(
            f"expand_zoom_option must be one of: {', '.join(EDIT_IMAGE_EXPAND_ZOOM_OPTIONS)}"))

    if custom_prompt is None and expand_zoom_option is None:
        raise _edit_image_fail(IncorrectValidationException('custom_prompt or expand_zoom_option is required'))

    values = {field: payload[field] for field in EDIT_IMAGE_ID_FIELDS}
    values['image_name'] = payload['image_name'].strip()
    values['image_id'] = payload['image_id'].strip()
    values['n_variations'] = n_variations
    values['custom_prompt'] = custom_prompt
    values['expand_zoom_option'] = expand_zoom_option
    return values


def _edit_image_parent_account_id(account: Dict[str, Any]) -> Any:
    """Req 5.3: attributes.parent_account.data.id when all levels are non-empty dicts and data has 'id'; else account['id']."""
    attributes = account.get('attributes')
    if isinstance(attributes, dict) and attributes:
        parent_account = attributes.get('parent_account')
        if isinstance(parent_account, dict) and parent_account:
            data = parent_account.get('data')
            if isinstance(data, dict) and data and 'id' in data:
                return data['id']
    return account.get('id')


def _edit_image_has_banner_image(ad_variant: Any, image_id: str) -> bool:
    """Req 8.1-8.3: True if any dict in Banner_Images has an 'image_id' exactly equal (==) to image_id."""
    banner_images = []  # type: List[Any]
    if isinstance(ad_variant, dict):
        attributes = ad_variant.get('attributes')
        if isinstance(attributes, dict):
            candidate = attributes.get('media_images_banner')
            if isinstance(candidate, list):
                banner_images = candidate
    for item in banner_images:
        if isinstance(item, dict) and 'image_id' in item and item['image_id'] == image_id:
            return True
    return False


def _edit_image_build_fury_payload(values: Dict[str, Any]) -> Dict[str, Any]:
    """Req 9.2-9.3: exactly the 10 keys of AdVariantImageEditCreate, image_id mapped to id_base_image."""
    return {
        'brand_id': values['brand_id'],
        'campaign_id': values['campaign_id'],
        'ad_id': values['ad_id'],
        'channel_id': values['channel_id'],
        'variant_id': values['variant_id'],
        'image_name': values['image_name'],
        'id_base_image': values['image_id'],
        'n_variations': values['n_variations'],
        'custom_prompt': values['custom_prompt'],
        'expand_zoom_option': values['expand_zoom_option'],
    }


def _edit_image_extract_job_id(response: Any) -> str:
    """Req 9.4, 9.7: return data.edit_job_id unchanged if it is a non-blank str; otherwise raise FuryException."""
    if isinstance(response, dict):
        data = response.get('data')
        if isinstance(data, dict):
            job_id = data.get('edit_job_id')
            if isinstance(job_id, str) and job_id.strip() != '':
                return job_id
    raise _edit_image_fail(FuryException('Fury response does not contain edit_job_id'))

class SelectAdUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.account_repo = AccountRepository()
        self.campaign_repo = CampaignRepository()
        self.ad_channel_repo = AdChannelRepository()

    def execute(self, payload):
        brand_id = payload.get('brand_id')
        campaign_id = payload.get('campaign_id')
        ad_id = payload.get('ad_id')
        channel_id = payload.get('channel_id')
        variant_id = payload.get('variant_id')

        account = self.account_repo.get_by_email(self.account_email)
        if not account:
            raise DataNotFoundException('Account not found')
        
        parent_account_id = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

        # Get campaign by id, brand_id, parent_account_id
        campaign = self.campaign_repo.get_by_id_brand_and_account(campaign_id, brand_id, parent_account_id)
        if not campaign:
            raise DataNotFoundException('Campaign not found or does not belong to account')

        # Get ad_channels by ad_id, channel_id
        ad_channels = self.ad_channel_repo.get_by_ad_and_channel_id(ad_id, channel_id)
        if not ad_channels:
            raise DataNotFoundException('No ad channels found')
        
        # Buscar si ad_channels contiene el variant_id
        variant_exists = any(ad_channel.get('id') == variant_id for ad_channel in ad_channels)
        if not variant_exists:
            raise DataNotFoundException('Variant ID not found in ad channels')

        # Update selected attribute
        for ad_channel in ad_channels:
            ad_channel_id = ad_channel.get('id')
            is_selected = (ad_channel_id == variant_id)
            self.ad_channel_repo.update(ad_channel_id, {'selected': is_selected})

        # Return selected ad details
        selected_ad_details = {
            'brand_id': brand_id,
            'campaign_id': campaign_id,
            'ad_id': ad_id,
            'channel_id': channel_id,
            'variant_id': variant_id,
            'ad_content': 'Contenido del anuncio seleccionado'
        }

        return {}
    
class DeleteAdUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.account_repo = AccountRepository()
        self.campaign_repo = CampaignRepository()
        self.ad_channel_repo = AdChannelRepository()

    def execute(self, payload):
        brand_id = payload.get('brand_id')
        campaign_id = payload.get('campaign_id')
        ad_id = payload.get('ad_id')
        channel_id = payload.get('channel_id')
        variant_id = payload.get('variant_id')

        account = self.account_repo.get_by_email(self.account_email)
        if not account:
            raise DataNotFoundException('Account not found')
        
        parent_account_id = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

        # Get campaign by id, brand_id, parent_account_id
        campaign = self.campaign_repo.get_by_id_brand_and_account(campaign_id, brand_id, parent_account_id)
        if not campaign:
            raise DataNotFoundException('Campaign not found or does not belong to account')
        
        # Get ad_channel by id, ad_id and channel_id to validate existence of ad and variant
        ad_channel = self.ad_channel_repo.get_by_id_and_ad_and_channel(variant_id, ad_id, channel_id)
        if not ad_channel:
            raise DataNotFoundException('Ad channel not found for the given ad and channel')
        
        # Delete ad_channel by id
        data = self.ad_channel_repo.delete_by_id(variant_id)
        if not data:
            raise DataNotFoundException('Failed to delete ad channel, it may not exist')

        return {}

class UpdateAdChannelGenerationFuryUseCase():
    def __init__(self):
        self.ad_channel_repo = AdChannelRepository()

    def execute(self, ad_id, payload):
        batch_id = payload.get('batch_id')
        if not batch_id:
            logger.error("batch_id is required in the payload")
            raise ValueError('batch_id is required in the payload')
        
        image_ids = payload.get('image_ids', [])

        # buscar ad_channel por ad_id para validar que existe antes de actualizar
        ad_channel = self.ad_channel_repo.get_ad_by_id(ad_id)
        if not ad_channel:
            logger.error(f"Ad channel not found for the given ad ID: {ad_id}")
            raise DataNotFoundException('Ad channel not found for the given ad ID')
        
        media_images_banner = ad_channel.get('attributes', {}).get('media_images_banner', [])

        for media in media_images_banner:
            img = next((image for image in image_ids if image.get('image_name', '') == media.get('name')), None)
            if img:
                media['image_id'] = img.get('image_id')
        

        # Update ad channel with batch_id for tracking
        request_datetime = datetime.now(timezone.utc).isoformat()
        success = self.ad_channel_repo.update(ad_id, {'media_generation_request_id': batch_id,
                                                      'media_generation_request_pending': True,
                                                      'media_generation_request_datetime': request_datetime,
                                                      'media_images_banner': media_images_banner})
        if not success:
            logger.error(f"Failed to update ad channel with batch ID: {batch_id} for ad ID: {ad_id}")
            raise DataNotFoundException('Ad channel not found or failed to update with batch ID')

        return {'ok': True}
    
class GenerateAnAdVariantUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.account_repo = AccountRepository()
        self.campaign_repo = CampaignRepository()
        self.ad_channel_repo = AdChannelRepository()
        self.brand_repository = BrandRepository()
        self.fury_client = FuryClient()
        self.ad_repository = AdRepository()

    def execute(self, payload):
        brand_id = payload.get('brand_id')
        campaign_id = payload.get('campaign_id')
        ad_id = payload.get('ad_id')
        channel_id = payload.get('channel_id')
        variant_id = payload.get('variant_id')
        add_variant = payload.get('add_variant', True)
        custom_prompt = payload.get('custom_prompt')
        n_variants = 1

        if not brand_id or not campaign_id or not ad_id or not channel_id:
            logger.error("Missing required parameters")
            raise ParametersNotFoundException('brand_id, campaign_id, ad_set_id and n_variants are required')
        
        if not add_variant and not variant_id:
            logger.error("variant_id is required when add_variant is false")
            raise ParametersNotFoundException('variant_id is required when add_variant is false')

        account = self.account_repo.get_by_email(self.account_email)
        if not account:
            logger.error(f"Account not found: {self.account_email}")
            raise DataNotFoundException('Account not found')
        
        parent_account_id = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

        brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account_id)
        if not brand:
            logger.error(f"Brand not found: {brand_id}")
            raise DataNotFoundException('Brand not found')

        # Get campaign by id, brand_id, parent_account_id
        campaign = self.campaign_repo.get_by_id_brand_and_account(campaign_id, brand_id, parent_account_id)
        if not campaign:
            logger.error(f"Campaign not found: {campaign_id} for brand {brand_id} and account {parent_account_id}")
            raise DataNotFoundException('Campaign not found or does not belong to account')
        
        # Get ad by id to validate existence of ad and variant 
        populate = ['ad_set_ref2.media_platform_project_id', 'channel_ref']       
        ad = self.ad_repository.get_by_id(ad_id, populate)
        if not ad:
            logger.error(f"Ad not found: {ad_id}")
            raise DataNotFoundException('Ad not found for the given ID')
        
        ad_set = ad.get('attributes', {}).get('ad_set_ref2', {}).get('data', {})
        media_platform_project_id = ad_set.get('attributes', {}).get('media_platform_project_id', {}).get('data', {}).get('id', 0)

        if not media_platform_project_id:
            logger.error(f"Ad set does not have a media platform project associated")
            raise DataNotFoundException('Ad set does not have a media platform project associated')

        logger.info(f"Generating {n_variants} ad variant(s) for ad_id: {ad_id}, channel_id: {channel_id}, variant_id: {variant_id} using media platform project id: {media_platform_project_id}")
        
        try:
            response = self.fury_client.post('/api/v2/variants', {'id_adset': ad_set.get('id'), 
                                                                  'n_variants': n_variants, 
                                                                  'project_id': str(media_platform_project_id),
                                                                  'id_ad': ad_id,
                                                                  'custom_prompt': str(custom_prompt) if custom_prompt else None,
                                                                  'add_variant': add_variant,
                                                                  'id_variant': [variant_id] if variant_id else None})
            return {'job_id': response.get('data', {}).get('variant_job_id')}
        except Exception as e:
            logger.error(f"Error generating ad variations: {str(e)}")
            raise e
        
class GenerateAllAdVariantUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.account_repo = AccountRepository()
        self.campaign_repo = CampaignRepository()
        self.ad_channel_repo = AdChannelRepository()
        self.brand_repository = BrandRepository()
        self.fury_client = FuryClient()
        self.ad_repository = AdRepository()

    def execute(self, payload):
        brand_id = payload.get('brand_id')
        campaign_id = payload.get('campaign_id')
        ad_id = payload.get('ad_id')
        channel_id = payload.get('channel_id')
        add_variant = payload.get('add_variant', True)
        custom_prompt = payload.get('custom_prompt')
        n_variants = payload.get('n_variants', 3)  # Default to generating 3 variants if not specified

        if not brand_id or not campaign_id or not ad_id or not channel_id:
            logger.error("Missing required parameters")
            raise ParametersNotFoundException('brand_id, campaign_id, ad_set_id and n_variants are required')
        
        # Validar que n_variants sea un número entero positivo mayor a 0
        if not isinstance(n_variants, int) or n_variants <= 0:
            logger.error("n_variants must be a positive integer greater than 0")
            raise ParametersNotFoundException('n_variants must be a positive integer greater than 0')

        account = self.account_repo.get_by_email(self.account_email)
        if not account:
            logger.error(f"Account not found: {self.account_email}")
            raise DataNotFoundException('Account not found')
        
        parent_account_id = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

        brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account_id)
        if not brand:
            logger.error(f"Brand not found: {brand_id}")
            raise DataNotFoundException('Brand not found')

        # Get campaign by id, brand_id, parent_account_id
        campaign = self.campaign_repo.get_by_id_brand_and_account(campaign_id, brand_id, parent_account_id)
        if not campaign:
            logger.error(f"Campaign not found: {campaign_id} for brand {brand_id} and account {parent_account_id}")
            raise DataNotFoundException('Campaign not found or does not belong to account')
        
        # Get ad by id to validate existence of ad and variant 
        populate = ['ad_set_ref2.media_platform_project_id', 'channel_ref']
        if not add_variant:
            populate.append('ad_channels')
        
        ad = self.ad_repository.get_by_id(ad_id, populate)
        if not ad:
            logger.error(f"Ad not found: {ad_id}")
            raise DataNotFoundException('Ad not found for the given ID')
        
        ad_set = ad.get('attributes', {}).get('ad_set_ref2', {}).get('data', {})
        media_platform_project_id = ad_set.get('attributes', {}).get('media_platform_project_id', {}).get('data', {}).get('id', 0)

        if not media_platform_project_id:
            logger.error(f"Ad set does not have a media platform project associated")
            raise DataNotFoundException('Ad set does not have a media platform project associated')
        
        existing_variant_ids = []
        if not add_variant:
            ad_channels = ad.get('attributes', {}).get('ad_channels', {}).get('data', [])
            existing_variant_ids = [ad_channel.get('id') for ad_channel in ad_channels]
        
        logger.info(f"Generating ad variants for ad_id: {ad_id}, channel_id: {channel_id} using media platform project id: {media_platform_project_id}")

        try:
            response = self.fury_client.post('/api/v2/variants', {'id_adset': ad_set.get('id'), 
                                                                  'n_variants': n_variants, 
                                                                  'project_id': str(media_platform_project_id),
                                                                  'id_ad': ad_id,
                                                                  'custom_prompt': str(custom_prompt) if custom_prompt else None,
                                                                  'add_variant': add_variant,
                                                                  'id_variant': existing_variant_ids if existing_variant_ids else None})
            return {'job_id': response.get('data', {}).get('variant_job_id')}
        except Exception as e:
            logger.error(f"Error generating ad variations: {str(e)}")
            raise e

class DeleteAdsVariantsFuryUseCase():
    def __init__(self):
        self.ad_channel_repo = AdChannelRepository()

    def execute(self, payload):
        variant_ids = payload.get('variant_ids')
        if not variant_ids or not isinstance(variant_ids, list):
            logger.error("No variant IDs provided for deletion")
            raise ValueError('variant_ids list cannot be empty')
        
        for variant_id in variant_ids:
            # Delete ad_channel by id
            success = self.ad_channel_repo.delete_by_id(variant_id)
            if not success:
                logger.warning(f"Ad channel with ID {variant_id} not found or failed to delete")
            else:
                logger.info(f"Ad channel with ID {variant_id} successfully deleted")

        return {'ok': True}
    
class AbyssaleVisualEditUseCase():
    def __init__(self):
        self.abyssale_visual_repo = AbyssaleVisualAdChannelRepository()
        self.ad_channel_repo = AdChannelRepository()

    def execute(self, payload):
        sharing_id = payload.get('sharing_id')
        if not sharing_id:
            logger.error('sharing_id is required in the payload')
            raise ValueError('sharing_id is required in the payload')

        mapping = self.abyssale_visual_repo.get_by_sharing_id(sharing_id)
        if not mapping:
            logger.info(f'No abyssale visual mapping found for sharing_id: {sharing_id}')
            return {'ok': False}

        ad_channel_relation = mapping.get('attributes', {}).get('ad_channel', {})
        ad_channel_data = ad_channel_relation.get('data') if isinstance(ad_channel_relation, dict) else None
        if not ad_channel_data:
            logger.info(f'No ad_channel relation found for abyssale visual mapping: {sharing_id}')
            return {'ok': False}

        ad_channel_id = ad_channel_data.get('id')
        attributes = ad_channel_data.get('attributes', {})
        media_formats = attributes.get('media_formats', [])
        if not isinstance(media_formats, list):
            logger.warning(f'media_formats is not a list for ad_channel_id: {ad_channel_id}')
            return {'ok': False}

        updated_media_formats = []
        updated = False
        for media_format in media_formats:
            if media_format.get('sharing_id') == sharing_id:
                updated_media_formats.append({
                    **media_format,
                    'visual_id': payload.get('id'),
                    'visual_url': payload.get('file', {}).get('url')
                })
                updated = True
            else:
                updated_media_formats.append(media_format)

        if not updated:
            logger.info(f'No media format found for sharing_id: {sharing_id} in ad_channel_id: {ad_channel_id}')
            return {'ok': False}

        success = self.ad_channel_repo.update(ad_channel_id, {'media_formats': updated_media_formats})
        if not success:
            logger.error(f'Failed to update ad channel with ID: {ad_channel_id}')
            raise DataNotFoundException('Ad channel not found or failed to update')

        return {'ok': True}

class PinFormatAdVariantUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.account_repo = AccountRepository()
        self.campaign_repo = CampaignRepository()
        self.ad_channel_repo = AdChannelRepository()
        self.brand_repo = BrandRepository()
        self.ad_repo = AdRepository()

    def execute(self, payload):
        brand_id = payload.get('brand_id')
        campaign_id = payload.get('campaign_id')
        ad_id = payload.get('ad_id')
        channel_id = payload.get('channel_id')
        variant_id = payload.get('variant_id')
        format_id = payload.get('format_id')

        if not all([brand_id, campaign_id, ad_id, channel_id, variant_id, format_id]):
            logger.error("Missing required parameters")
            raise ParametersNotFoundException('All parameters are required')
        
        # Get account and validate access
        account = self.account_repo.get_by_email(self.account_email)
        if not account:
            logger.error(f"Account not found: {self.account_email}")
            raise DataNotFoundException('Account not found')
        
        parent_account_id = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

        campaign = self.campaign_repo.get_by_id_brand_and_account(campaign_id, brand_id, parent_account_id)
        if not campaign:
            logger.error(f"Campaign not found: {campaign_id} for brand {brand_id} and account {parent_account_id}")
            raise DataNotFoundException('Campaign not found or does not belong to account')

        populate = ['ad_set_ref2.media_platform_project_id', 'channel_ref']
        ad = self.ad_repo.get_by_id(ad_id, populate)
        if not ad:
            logger.error(f"Ad not found: {ad_id}")
            raise DataNotFoundException('Ad not found for the given ID')

        ad_channel = self.ad_channel_repo.get_by_id_and_ad_and_channel(variant_id, ad_id, channel_id)
        if not ad_channel:
            logger.error(f"Ad channel not found: {variant_id} for ad {ad_id} and channel {channel_id}")
            raise DataNotFoundException('Ad variant not found')

        media_formats = ad_channel.get('attributes', {}).get('media_formats', [])
        if not isinstance(media_formats, list):
            logger.error(f"No media formats found in ad channel: {variant_id}")
            raise DataNotFoundException('No media formats found in ad variant')

        format_exists = any(f.get('id') == format_id for f in media_formats)
        if not format_exists:
            logger.error(f"Format not found in ad channel: {format_id}")
            raise DataNotFoundException('Format not found in ad variant')

        currently_pinned = next((f for f in media_formats if f.get('pinned') is True), None)
        pinned_format_id = currently_pinned.get('id') if currently_pinned else None

        updated_formats = []
        for fmt in media_formats:
            is_requested_format = fmt.get('id') == format_id
            fmt_copy = {**fmt}
            fmt_copy['pinned'] = is_requested_format
            updated_formats.append(fmt_copy)

        update_data = {
            'media_formats': updated_formats
        }
        
        success = self.ad_channel_repo.update(variant_id, update_data)
        if not success:
            logger.error(f"Failed to update ad channel: {variant_id}")
            raise DataNotFoundException('Failed to update ad variant')

        return {
            'variant_id': variant_id,
            'pinned_format_id': format_id,
            'previous_pinned_format_id': pinned_format_id,
            'formats': [
                {
                    'id': format.get('id'),
                    'uid': format.get('uid'),
                    'unit': format.get('unit'),
                    'width': format.get('width'),
                    'height': format.get('height'),
                    'errors': format.get('errors'),
                    'pinned': format.get('pinned'),
                    'visual_id': format.get('visual_id'),
                    'sharing_id': format.get('sharing_id'),
                    'visual_url': format.get('visual_url'),
                    'preview_url': format.get('preview_url')
                }
                for format in updated_formats
            ]
        }


class UnpinFormatAdVariantUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.account_repo = AccountRepository()
        self.campaign_repo = CampaignRepository()
        self.ad_channel_repo = AdChannelRepository()
        self.brand_repo = BrandRepository()
        self.ad_repo = AdRepository()

    def execute(self, payload):
        brand_id = payload.get('brand_id')
        campaign_id = payload.get('campaign_id')
        ad_id = payload.get('ad_id')
        channel_id = payload.get('channel_id')
        variant_id = payload.get('variant_id')

        if not all([brand_id, campaign_id, ad_id, channel_id, variant_id]):
            logger.error("Missing required parameters")
            raise ParametersNotFoundException('All parameters are required')

        # Get account and validate access
        account = self.account_repo.get_by_email(self.account_email)
        if not account:
            logger.error(f"Account not found: {self.account_email}")
            raise DataNotFoundException('Account not found')

        parent_account_id = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']

        campaign = self.campaign_repo.get_by_id_brand_and_account(campaign_id, brand_id, parent_account_id)
        if not campaign:
            logger.error(f"Campaign not found: {campaign_id} for brand {brand_id} and account {parent_account_id}")
            raise DataNotFoundException('Campaign not found or does not belong to account')

        populate = ['ad_set_ref2.media_platform_project_id', 'channel_ref']
        ad = self.ad_repo.get_by_id(ad_id, populate)
        if not ad:
            logger.error(f"Ad not found: {ad_id}")
            raise DataNotFoundException('Ad not found for the given ID')

        ad_channel = self.ad_channel_repo.get_by_id_and_ad_and_channel(variant_id, ad_id, channel_id)
        if not ad_channel:
            logger.error(f"Ad channel not found: {variant_id} for ad {ad_id} and channel {channel_id}")
            raise DataNotFoundException('Ad variant not found')

        media_formats = ad_channel.get('attributes', {}).get('media_formats', [])
        if not isinstance(media_formats, list):
            logger.error(f"No media formats found in ad channel: {variant_id}")
            raise DataNotFoundException('No media formats found in ad variant')

        currently_pinned = next((f for f in media_formats if f.get('pinned') is True), None)
        pinned_format_id = currently_pinned.get('id') if currently_pinned else None

        updated_formats = []
        for fmt in media_formats:
            fmt_copy = {**fmt}
            fmt_copy['pinned'] = False
            updated_formats.append(fmt_copy)

        update_data = {
            'media_formats': updated_formats
        }

        success = self.ad_channel_repo.update(variant_id, update_data)
        if not success:
            logger.error(f"Failed to update ad channel: {variant_id}")
            raise DataNotFoundException('Failed to update ad variant')

        return {
            'variant_id': variant_id,
            'previous_pinned_format_id': pinned_format_id,
            'formats': [
                {
                    'id': format.get('id'),
                    'uid': format.get('uid'),
                    'unit': format.get('unit'),
                    'width': format.get('width'),
                    'height': format.get('height'),
                    'errors': format.get('errors'),
                    'pinned': format.get('pinned'),
                    'visual_id': format.get('visual_id'),
                    'sharing_id': format.get('sharing_id'),
                    'visual_url': format.get('visual_url'),
                    'preview_url': format.get('preview_url')
                }
                for format in updated_formats
            ]
        }

def _preserve_pinned_format(source_variant_id, new_variant_id):
    """Copy the pinned media format status from a source ad variant to a new one.

    Fetches the source variant's media_formats, finds the format marked as
    pinned (if any), and updates the new variant's formats so the same format
    id is pinned there too. This is used to keep the pinned selection when an
    ad variant is duplicated.

    Note: As of this writing there is no ad-variant "duplication" workflow in
    either the Sinergia or Fury codebases (the closest flow,
    GenerateAnAdVariantUseCase/GenerateAllAdVariantUseCase with
    add_variant=False, replaces variants by generating new ad_channels and
    deleting the old ones - it does not clone an existing variant while
    keeping both). This helper is implemented ahead of that feature so that
    whenever a real duplication workflow is added, it can call
    _preserve_pinned_format(source_variant_id, new_variant_id) right after
    creating the duplicate ad_channel to carry over the pinned format.
    See spec: ads-pin-format-variant, Requirement 3.1.

    Args:
        source_variant_id: ad_channel ID of the variant to copy the pinned
            status from.
        new_variant_id: ad_channel ID of the newly created variant that
            should receive the pinned status.

    Returns:
        The updated ad_channel data on success, or False/None if there was
        nothing to copy or the update failed.
    """
    ad_channel_repo = AdChannelRepository()

    source_ad_channel = ad_channel_repo.get_ad_by_id(source_variant_id)
    if not source_ad_channel:
        logger.error(f"Source ad variant not found: {source_variant_id}")
        return False

    media_formats = source_ad_channel.get('attributes', {}).get('media_formats', [])
    if not isinstance(media_formats, list):
        logger.error(f"No media formats found in source ad variant: {source_variant_id}")
        return False

    pinned_format = next((f for f in media_formats if f.get('pinned') is True), None)
    if not pinned_format:
        logger.info(f"No pinned format found in source ad variant: {source_variant_id}")
        return False

    new_formats = [
        {
            'id': fmt.get('id'),
            'uid': fmt.get('uid'),
            'unit': fmt.get('unit'),
            'width': fmt.get('width'),
            'height': fmt.get('height'),
            'errors': fmt.get('errors'),
            'pinned': fmt.get('id') == pinned_format.get('id'),
            'visual_id': fmt.get('visual_id'),
            'sharing_id': fmt.get('sharing_id'),
            'visual_url': fmt.get('visual_url'),
            'preview_url': fmt.get('preview_url')
        }
        for fmt in media_formats
    ]

    update_data = {
        'media_formats': new_formats
    }

    success = ad_channel_repo.update(new_variant_id, update_data)
    if not success:
        logger.error(f"Failed to update new ad variant: {new_variant_id}")
        return False

    return success


class EditAdVariantImageUseCase():
    """Validate an image edit request and enqueue the edit job in Fury."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.account_repo = AccountRepository()
        self.campaign_repo = CampaignRepository()
        self.ad_channel_repo = AdChannelRepository()
        self.fury_client = FuryClient()

    def execute(self, payload: Dict[str, Any]) -> Dict[str, str]:
        # Req 3 and 4: presence first, then values (no collaborator calls on failure)
        _edit_image_check_presence(payload)
        values = _edit_image_validate(payload)

        # Req 5: account and Parent_Account (repository exceptions propagate unchanged)
        account = self.account_repo.get_by_email(self.user_id)
        if not account:
            raise _edit_image_fail(DataNotFoundException('Account not found'))
        parent_account_id = _edit_image_parent_account_id(account)

        # Req 6: campaign must belong to brand and account
        campaign = self.campaign_repo.get_by_id_brand_and_account(
            values['campaign_id'], values['brand_id'], parent_account_id)
        if not campaign:
            raise _edit_image_fail(DataNotFoundException('Campaign not found or does not belong to account'))

        # Req 7: variant must belong to ad, campaign and channel
        ad_variant = self.ad_channel_repo.get_by_id_ad_campaign_and_channel(
            values['variant_id'], values['ad_id'], values['campaign_id'], values['channel_id'])
        if not ad_variant:
            raise _edit_image_fail(DataNotFoundException('Ad variant not found'))

        # Req 8: image must be one of the variant banners
        if not _edit_image_has_banner_image(ad_variant, values['image_id']):
            raise _edit_image_fail(DataNotFoundException('Image not found in ad variant'))

        # Req 9: enqueue in Fury; log the prompt length only, never its text
        fury_edit_payload = _edit_image_build_fury_payload(values)
        prompt = values['custom_prompt']
        logger.info(
            f"Enqueuing image edit for variant_id: {values['variant_id']}, "
            f"image_id: {values['image_id']}, n_variations: {values['n_variations']}, "
            f"expand_zoom_option: {values['expand_zoom_option']}, "
            f"custom_prompt_length: {len(prompt) if prompt else 0}")
        try:
            response = self.fury_client.post(EDIT_IMAGE_FURY_ENDPOINT, fury_edit_payload)
        except SinergiaException:
            raise
        except Exception as e:
            raise _edit_image_fail(FuryException('Failed to enqueue image edit job in Fury')) from e
        return {'job_id': _edit_image_extract_job_id(response)}
