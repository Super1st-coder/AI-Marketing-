import logging

from app.exceptions.base import DataNotFoundException, ParametersNotFoundException
from app.v2.repository.account import AccountRepository
from app.v2.repository.brand import BrandRepository
from app.v2.repository.campaign_channel_publish import CampaignChannelPublishRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GetACampaignByMetaIDUseCase():
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.account_repository = AccountRepository()
        self.brand_repository = BrandRepository()
        self.campaign_channel_publish_repository = CampaignChannelPublishRepository()

    def _get_account(self):
        account = self.account_repository.get_by_email(self.user_id)
        if not account:
            logger.error(f"Account not found: {self.user_id}")
            raise DataNotFoundException('Account not found')
        return account

    def _get_parent_account(self):
        account = self._get_account()
        parent_account = (
            account['attributes']['parent_account']['data']['id']
            if account.get('attributes', {}).get('parent_account', {}).get('data')
            else account['id']
        )
        return parent_account

    def _build_response(self, campaign_publish):
        publish_attributes = campaign_publish.get('attributes', {})
        campaign = publish_attributes.get('campaign_id', {}).get('data') or campaign_publish.get('campaign_id')

        if not campaign:
            logger.error(f"Campaign relation not found in campaign_publish: {campaign_publish}")
            raise DataNotFoundException('Campaign relation not found')

        campaign_attributes = campaign.get('attributes', {})
        brand = campaign_attributes.get('brand_ref', {}).get('data') or {}
        project = campaign_attributes.get('project_ref', {}).get('data') or {}
        umbrella_campaign = campaign_attributes.get('ucampaign_ref', {}).get('data') or {}
        product = project.get('attributes', {}).get('product_ref', {}).get('data') or {}
        buyer_person = project.get('attributes', {}).get('bperson_ref', {}).get('data') or {}

        return {
            'brand_id': brand.get('id'),
            'brand_name': brand.get('attributes', {}).get('name'),
            'campaign_id': campaign.get('id'),
            'campaign_name': campaign_attributes.get('name'),
            'project_id': project.get('id'),
            'project_name': project.get('attributes', {}).get('name'),
            'umbrella_campaign_id': umbrella_campaign.get('id'),
            'umbrella_campaign_name': umbrella_campaign.get('attributes', {}).get('name'),
            'buyer_person_id': buyer_person.get('id'),
            'buyer_person_name': buyer_person.get('attributes', {}).get('name'),
            'product_id': product.get('id'),
            'product_name': product.get('attributes', {}).get('name'),
        }

    def execute(self, meta_campaign_id):
        if not meta_campaign_id:
            logger.error("Meta Campaign Id is required")
            raise ParametersNotFoundException('Meta Campaign Id is required')

        parent_account = self._get_parent_account()

        campaign = self.campaign_channel_publish_repository.get_by_meta_campaign_id_and_brand_account(
            meta_campaign_id,
            parent_account,
        )

        if not campaign:
            logger.error(
                f"CampaignChannelPublish not found for meta_campaign_id={meta_campaign_id}, "
                f"parent_account={parent_account}"
            )
            raise DataNotFoundException('Campaign not found for the given Meta campaign and account')

        return self._build_response(campaign)