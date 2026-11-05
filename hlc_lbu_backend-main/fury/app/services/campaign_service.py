"""Campaign service - Business logic for campaigns"""
from typing import Dict, Any
from utils.strapi_client import StrapiClient
from core.logging import get_logger

logger = get_logger(__name__)


class CampaignService:
    """Service for campaign operations"""
    
    def __init__(self, strapi_client: StrapiClient):
        self.strapi = strapi_client
    
    def validate_campaign(self, campaign_id: str, email: str) -> Dict[str, Any]:
        """
        Validate campaign.
        In the original flow this calls an n8n workflow.
        For now, we simulate or make a direct call.
        """
        # TODO: Implement real n8n workflow call if needed
        logger.info(f"Validating campaign: {campaign_id} for {email}")
        
        # For now, return expected structure
        return {
            "campaign": {
                "id": campaign_id,
                "attributes": {
                    "name": "Sample Campaign",
                    "language": "Spanish",
                    "preferred_campaign": {
                        "sections": {
                            "campaign_details": {
                                "text": "Campaign details text"
                            }
                        }
                    }
                }
            }
        }
    
    def get_ad_channel(self, ad_id: int, channel_id: int) -> Dict[str, Any]:
        """Get ad channel from Strapi"""
        return self.strapi.get_ad_channel(ad_id, channel_id)
    
    def get_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Get campaign with all relationships"""
        return self.strapi.get_campaign(campaign_id)
    
    def calculate_intention_max_char(self, element: Dict[str, Any]) -> Dict[str, int]:
        """Calculate character limits for each intention"""
        intention_max_char = {
            "headline": 55,
            "hook": 55,
            "punchline": 55,
            "legal": 55,
            "description": 125,
            "discount": 55,
            "pricing": 55,
            "offer": 55,
            "benefit1": 55,
            "benefit2": 55,
            "benefit3": 55,
            "feature1": 55,
            "feature2": 55,
            "feature3": 55,
            "cta": 55
        }
        
        if element.get("intention") and element.get("max_char"):
            intention = element["intention"].lower()
            intention_max_char[intention] = element["max_char"]
        
        return intention_max_char
    
    def prepare_agent_fields(
        self,
        validate_campaign_result: Dict,
        get_campaign_result: Dict,
        get_ad_channel_result: Dict,
        element: Dict[str, Any],
        intention_max_char: Dict[str, int]
    ) -> Dict[str, Any]:
        """Prepare fields needed for AI agent"""
        campaign_data = get_campaign_result.get("data", [{}])[0]
        campaign_attrs = campaign_data.get("attributes", {})
        project_ref = campaign_attrs.get("project_ref", {}).get("data", {}).get("attributes", {})
        bperson_ref = project_ref.get("bperson_ref", {}).get("data", {}).get("attributes", {})
        product_ref = project_ref.get("product_ref", {}).get("data", {}).get("attributes", {})
        ucampaign_ref = campaign_attrs.get("ucampaign_ref", {}).get("data", {}).get("attributes", {})
        
        ad_channel_data = get_ad_channel_result.get("data", [{}])[0]
        ad_channel_attrs = ad_channel_data.get("attributes", {})
        channel_ref = ad_channel_attrs.get("channel_ref", {}).get("data", {}).get("attributes", {})
        channel_group_ref = channel_ref.get("channel_group_ref", {}).get("data", {}).get("attributes", {})
        
        campaign_validate = validate_campaign_result.get("campaign", {}).get("attributes", {})
        
        return {
            "language": campaign_validate.get("language", "English"),
            "chat_memory_key": f"Ad-Channel-texts-attributes-{validate_campaign_result['campaign']['id']}-{ad_channel_data.get('id')}",
            "bperson_collection_id": bperson_ref.get("collection_id", "empty"),
            "buyer_person_name": bperson_ref.get("name", " "),
            "campaign_details": campaign_validate.get("preferred_campaign", {}).get("sections", {}).get("campaign_details", {}).get("text", " "),
            "campaign_name": campaign_validate.get("name", ""),
            "umbrella_campaign_name": ucampaign_ref.get("preferred_umbrella_campaign", {}).get("title", " "),
            "product_name": product_ref.get("name", ""),
            "product_benefits": product_ref.get("mandatory_attributes_saved", {}).get("benefits", []),
            "product_features": product_ref.get("mandatory_attributes_saved", {}).get("features", []),
            "product_collection_id": product_ref.get("collection_id", "empty"),
            "channel_group_name": channel_group_ref.get("name", " "),
            "channel_name": channel_ref.get("name", " "),
            "intention_max_char": intention_max_char,
            "intention": element.get("intention", " "),
            "text": element.get("payload", " ")
        }

