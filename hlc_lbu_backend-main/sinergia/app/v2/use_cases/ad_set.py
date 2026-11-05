import logging
from datetime import datetime, timezone
from app.v2.repository.account import AccountRepository
from app.v2.repository.brand import BrandRepository
from app.v2.repository.media_platform_project import MediaPlatformProjectRepository
from app.v2.repository.ad_set import AdSetRepository
from app.v2.repository.ad_channel import AdChannelRepository
from app.v2.repository.channel import ChannelRepository
from app.exceptions.base import DataNotFoundException, ParametersNotFoundException
from app.tools.fury import FuryClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SetMediaPlatformProjectUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.account_repository = AccountRepository()
        self.brand_repository = BrandRepository()
        self.media_platform_repository = MediaPlatformProjectRepository()
        self.ad_set_repository = AdSetRepository()

    def execute(self, data):
        brand_id = data.get('brand_id')
        ad_set_id = data.get('ad_set_id')
        media_platform_project_id = data.get('media_platform_project_id')

        if not brand_id:
            logger.error("Brand id is required")
            raise ParametersNotFoundException('Brand Id is required')
        
        if not ad_set_id:
            logger.error("Ad set id is required")
            raise ParametersNotFoundException('Ad Set Id is required')

        account = self.account_repository.get_by_email(self.account_email)
        if not account:
            logger.error(f"Account not found: {self.account_email}")
            raise DataNotFoundException('Account not found')

        parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']
        brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account)
        if not brand:
            logger.error(f"Brand not found: {brand_id}")
            raise DataNotFoundException('Brand not found')

        if media_platform_project_id:
            project = self.media_platform_repository.get_by_brand_and_id(brand['id'], media_platform_project_id)
            if not project:
                logger.error(f"Media platform project not found: {media_platform_project_id}")
                raise DataNotFoundException('Media platform project not found')

        ad_set = self.ad_set_repository.get_by_id(ad_set_id)
        if not ad_set:
            logger.error(f"Ad set not found: {ad_set_id}")
            raise DataNotFoundException('Ad set not found')

        updated = self.ad_set_repository.update(ad_set_id, {'media_platform_project_id': media_platform_project_id})
        return {'id': updated['id'], 'media_platform_project_id': media_platform_project_id}

class GenerateAdVariationsUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.account_repository = AccountRepository()
        self.brand_repository = BrandRepository()
        self.ad_set_repository = AdSetRepository()
        self.fury_client = FuryClient()

    def execute(self, data):        
        brand_id = data.get('brand_id')
        campaign_id = data.get('campaign_id')
        ad_set_id = data.get('ad_set_id')
        n_variants = data.get('n_variants')

        if not brand_id or not campaign_id or not ad_set_id or not n_variants:
            logger.error("Missing required parameters")
            raise ParametersNotFoundException('brand_id, campaign_id, ad_set_id and n_variants are required')

        # Validar que n_variants sea un número entero positivo mayor a 0
        if not isinstance(n_variants, int) or n_variants <= 0:
            logger.error("n_variants must be a positive integer greater than 0")
            raise ParametersNotFoundException('n_variants must be a positive integer greater than 0')

        account = self.account_repository.get_by_email(self.account_email)
        if not account:
            logger.error(f"Account not found: {self.account_email}")
            raise DataNotFoundException('Account not found')

        parent_account = account['attributes']['parent_account']['data']['id'] if account['attributes']['parent_account']['data'] else account['id']
        brand = self.brand_repository.get_by_id_and_account(brand_id, parent_account)
        if not brand:
            logger.error(f"Brand not found: {brand_id}")
            raise DataNotFoundException('Brand not found')

        ad_set = self.ad_set_repository.get_by_id_and_campaign_and_brand(ad_set_id, campaign_id, brand_id)
        if not ad_set:
            logger.error(f"Ad set not found: {ad_set_id}")
            raise DataNotFoundException('Ad set not found')
        
        media_platform_project_id = ad_set.get('attributes', {}).get('media_platform_project_id', {}).get('data', {}).get('id', 0)

        if not media_platform_project_id:
            logger.error(f"Ad set {ad_set_id} does not have a media platform project associated")
            raise DataNotFoundException('Ad set does not have a media platform project associated')

        try:
            response = self.fury_client.post('/api/v2/variants', {'id_adset': ad_set_id, 
                                                                  'n_variants': n_variants, 
                                                                  'project_id': str(media_platform_project_id)})
            return {'job_id': response.get('data', {}).get('variant_job_id')}
        except Exception as e:
            logger.error(f"Error generating ad variations: {str(e)}")
            raise e
        
class GetJobResultGenerateAdVariationsUseCase():
    def __init__(self, account_email):
        self.account_email = account_email
        self.account_repository = AccountRepository()
        self.fury_client = FuryClient()

    def execute(self, job_id):        
        account = self.account_repository.get_by_email(self.account_email)
        if not account:
            logger.error(f"Account not found: {self.account_email}")
            raise DataNotFoundException('Account not found')
        
        if not job_id:
            logger.error("Job id is required")
            raise ParametersNotFoundException('Job Id is required')

        try:
            response = self.fury_client.get(f'/api/v2/jobs/{job_id}')
            return response.get('data')
        except Exception as e:
            logger.error(f"Error getting job result: {str(e)}")
            raise e
        
class GetAdSetUseCase():
    def __init__(self):
        self.ad_set_repository = AdSetRepository()

    def _build_response(self, ad_set):
        attrs = ad_set.get('attributes', {})
        funnel_flow = attrs.get('funnel_flow_ref', {}).get('data', {}).get('attributes', {})
        campaign_data = funnel_flow.get('campaign_ref', {}).get('data', {})
        campaign_attrs = campaign_data.get('attributes', {})
        umbrella_attrs = campaign_attrs.get('ucampaign_ref', {}).get('data', {}).get('attributes', {})

        # Ads from ads relation
        ads_data = attrs.get('ads', {}).get('data', [])
        ads = []
        if ads_data:
            for ad in ads_data:
                ad_attrs = ad.get('attributes', {})
                ads.append({
                    'id': ad.get('id'),
                    'name': ad_attrs.get('name'),
                    'description': ad_attrs.get('description')
                })

        # Audience from preferred_audience
        audiences_data = attrs.get('audiences', {}).get('data', [])
        preferred_audience = None
        if audiences_data:
            raw = audiences_data[0].get('attributes', {}).get('preferred_audience')
            if raw:
                preferred_audience = {
                    'name': raw.get('name'),
                    'description': raw.get('description'),
                    'gender': raw.get('gender'),
                    'age': raw.get('age', []),
                    'income': raw.get('income'),
                    'location': raw.get('location', []),
                    'interests': raw.get('interests', []),
                }

        # Creative angle from experiment_ref.subcategory_ref
        experiment_attrs = attrs.get('experiment_ref', {}).get('data', {}).get('attributes', {})
        subcategory = experiment_attrs.get('subcategory_ref', {}).get('data', {})
        creative_angle = None
        if subcategory:
            sub_attrs = subcategory.get('attributes', {})
            creative_angle = {
                'type': experiment_attrs.get('type'),
                'name': sub_attrs.get('name'),
                'description': sub_attrs.get('description'),
            }

        # Campaign from funnel_flow_ref.campaign_ref
        campaign = None
        if campaign_attrs:
            campaign = {
                'name': campaign_attrs.get('preferred_campaign', {}).get('campaign', {}).get('title'),
                'language': campaign_attrs.get('language'),
                'buyer': campaign_attrs.get('summary_saved', {}).get('bperson'),
                'product': campaign_attrs.get('summary_saved', {}).get('product'),
                'campaing': campaign_attrs.get('summary_saved', {}).get('campaign'),
                'product_details': campaign_attrs.get('product_details'),
                'bperson_details': campaign_attrs.get('bperson_details'),
            }
            campaign_sections = campaign_attrs.get('preferred_campaign', {}).get('sections') if campaign_attrs.get('preferred_campaign').get('sections') else []
            campaign_final_sections = {sub_item: campaign_sections[sub_item].get('text', '') for sub_item in campaign_sections for item in sub_item} if campaign_sections else {}
            campaign.update(campaign_final_sections)

        umbrella = None
        if umbrella_attrs:
            umbrella = {
                'title': umbrella_attrs.get('preferred_umbrella_campaign', {}).get('title'),
                'description': umbrella_attrs.get('preferred_umbrella_campaign', {}).get('description'),
                'benefit': {
                    'title': umbrella_attrs.get('preferred_benefit', {}).get('title'),
                    'description': umbrella_attrs.get('preferred_benefit', {}).get('text'),
                },
                'drama': {
                    'title': umbrella_attrs.get('preferred_drama', {}).get('title'),
                    'description': umbrella_attrs.get('preferred_drama', {}).get('text'),
                },
                'scene': {
                    'title': umbrella_attrs.get('preferred_scene', {}).get('title'),
                    'description': umbrella_attrs.get('preferred_scene', {}).get('text'),
                }
            }
            umbrella_summary = umbrella_attrs.get('summary_saved', {}).values() if umbrella_attrs.get('summary_saved') else []
            umbrella_final_summary = {item['id']: item['content']
                                      for sub_item in umbrella_summary for item in sub_item} if umbrella_summary else {}
            umbrella.update(umbrella_final_summary)

        # Brand from funnel_flow_ref.campaign_ref.brand_ref
        brand_data = campaign_attrs.get('brand_ref', {}).get('data', {})
        brand = None
        if brand_data:
            brand_attrs = brand_data.get('attributes', {})
            brand = {
                'id': brand_data.get('id'),
                'name': brand_attrs.get('name'),
                'identity': brand_attrs.get('identity'),
                'logos': brand_attrs.get('logos'),
                'colors': brand_attrs.get('colors'),
                'typography': brand_attrs.get('typography'),
                'dos_donts': brand_attrs.get('dos_donts'),
                'website': brand_attrs.get('website'),
            }

        # Buyer from funnel_flow_ref.campaign_ref.project_ref.bperson_ref
        project_attrs = campaign_attrs.get('project_ref', {}).get('data', {}).get('attributes', {})
        bperson_data = project_attrs.get('bperson_ref', {}).get('data', {})
        buyer = None
        if bperson_data:
            bp = bperson_data.get('attributes', {})
            attributes = bp.get('mandatory_attributes_saved', {})
            buyer = {
                'id': bperson_data.get('id'),
                'name': bp.get('name'),
                'story': bp.get('bperson_story'),
                'attributes': attributes,
            }

        # Product from funnel_flow_ref.campaign_ref.project_ref.product_ref
        product_data = project_attrs.get('product_ref', {}).get('data', {})
        product = None
        if product_data:
            prod = product_data.get('attributes', {})
            attributes = prod.get('mandatory_attributes_saved', {})
            product = {
                'id': product_data.get('id'),
                'name': prod.get('name'),
                'description': prod.get('description'),
                'story': prod.get('product_story'),
                'attributes': attributes,
            }

        return {
            'id': ad_set.get('id'),
            'name': attrs.get('name'),
            'audience': preferred_audience,
            'creative_angle': creative_angle,
            'umbrella': umbrella,
            'campaign': campaign,
            'brand': brand,
            'buyer': buyer,
            'product': product,
            'ads': ads
        }
    
    def execute(self, ad_set_id):
        if not ad_set_id:
            logger.error("Ad set id is required")
            raise ParametersNotFoundException('Ad Set Id is required')
       
        ad_set = self.ad_set_repository.get_by_id(ad_set_id, is_fury=True)

        if not ad_set:
            logger.error(f"Ad set not found: {ad_set_id}")
            raise DataNotFoundException('Ad set not found')

        return self._build_response(ad_set)


class SaveAdsVariantsFuryUseCase():
    def __init__(self):
        self.ad_set_repository = AdSetRepository()
        self.ad_channel_repository = AdChannelRepository()
        self.channel_repository = ChannelRepository()

    def _build_channel_attributes(self, channel_attrs_def, variant_attrs):
        payload_map = {a['name']: a.get('payloads', [{'id': 0, 'payload': ''}]) for a in variant_attrs}
        return [
            {**attr_def, 'payloads': payload_map.get(attr_def['name'], attr_def.get('payloads', []))}
            for attr_def in channel_attrs_def
        ]

    def _build_media_elements(self, media_elements):
        return [{**e, 'intention': None} for e in media_elements]

    def _build_media_formats(self, media_formats):
        return [{**e, 'pinned': False} for e in media_formats]

    def execute(self, ad_set_id: int, payload: dict):
        if not ad_set_id:
            raise ParametersNotFoundException('Ad Set Id is required')
        if not payload:
            raise ParametersNotFoundException('Payload is required')
        if not payload.get('ads'):
            raise ParametersNotFoundException('Ads are required')
        if not payload.get('ad_id'):
            raise ParametersNotFoundException('Ad Id is required')

        channel = self.channel_repository.get_by_name('Meta Ads')
        if not channel:
            raise DataNotFoundException('Meta Ads channel not found')
        channel_id = channel['id']
        channel_attrs_def = channel.get('attributes', {}).get('attributes', [])

        ad_set = self.ad_set_repository.get_by_id_with_ads(ad_set_id)
        if not ad_set:
            raise DataNotFoundException('Ad set not found')

        ads_list = ad_set.get('attributes', {}).get('ads', {}).get('data', [])
        if not ads_list:
            raise DataNotFoundException('No ads found in ad set')
        # Buscar payload.get('ad_id') en ads_list
        ad_id = None
        for ad in ads_list:
            if ad.get('id') == payload.get('ad_id'):
                ad_id = ad.get('id')
                break
        
        if not ad_id:
            raise DataNotFoundException('Ad ID not found in ad set')
        
        #ad_id = ads_list[0]['id']

        request_datetime = datetime.now(timezone.utc).isoformat()

        created = []
        for variant in payload.get('ads', []):
            channel_attributes = self._build_channel_attributes(
                channel_attrs_def, variant.get('channel_atributes', [])
            )
            media_elements = self._build_media_elements(variant.get('media_elements', []))
            media_formats = self._build_media_formats(variant.get('media_formats', []))
            result = self.ad_channel_repository.create({
                'ad_ref': ad_id,
                'ad_ref2': ad_id,
                'channel_ref': channel_id,
                'media_template_id': variant.get('media_template_id'),
                'media_template_name': variant.get('media_template_name'),
                'media_elements': media_elements,
                'media_images_banner': variant.get('media_images_banner'),
                'media_formats': media_formats,
                'channel_attributes': channel_attributes,
                'selected': False,
                'media_generation_request_datetime': request_datetime
            })
            created.append({'id': result['id'] if result else None})

        return {'ad_set_id': ad_set_id, 'ad_id': ad_id, 'created': created}