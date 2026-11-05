"""Ad generation endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from schemas.ad_generation import AdGenerationRequest, AdGenerationResponse
from schemas.common import ErrorResponse
from services.ad_generation_service import AdGenerationService
from services.campaign_service import CampaignService
from utils.strapi_client import StrapiClient
from utils.qdrant_client import QdrantClientWrapper
from utils.postgres_client import PostgresClientWrapper
from utils.langfuse_client import LangfuseClientWrapper
from core.exceptions import FuryException
from core.logging import get_logger
from core.auth import verify_internal_api_key

logger = get_logger(__name__)
router = APIRouter()


def get_ad_generation_service() -> AdGenerationService:
    """Get ad generation service instance"""
    strapi_client = StrapiClient()
    campaign_service = CampaignService(strapi_client)
    qdrant_client = QdrantClientWrapper()
    postgres_client = PostgresClientWrapper()
    langfuse_client = LangfuseClientWrapper()
    
    return AdGenerationService(
        campaign_service=campaign_service,
        qdrant_client=qdrant_client,
        postgres_client=postgres_client,
        langfuse_client=langfuse_client
    )


@router.post(
    "/generate_text",
    response_model=AdGenerationResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"description": "Unauthorized — missing or invalid X-Internal-API-Key"},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def generate_text(
    request: AdGenerationRequest,
    service: AdGenerationService = Depends(get_ad_generation_service),
    _: str = Depends(verify_internal_api_key),
):
    """
    Generate ad text using AI
    
    This endpoint implements the complete n8n workflow:
    1. Validates the campaign
    2. Gets ad channel information
    3. Retrieves campaign details
    4. Calculates character limits
    5. Generates text using AI with context from vector stores
    6. Returns the generated text
    
    Uses:
    - Strapi for campaign and ad channel data
    - PostgreSQL for chat memory
    - Qdrant for vector stores (customer and product context)
    - OpenAI for text generation
    - Langfuse for prompt management
    """
    try:
        logger.info(f"Generating text for campaign={request.campaign_id}, ad={request.ad_id}")
        
        result = service.generate_text(
            email=request.email,
            brand_id=request.brand_id,
            campaign_id=request.campaign_id,
            ad_id=request.ad_id,
            channel_id=request.channel_id,
            element=request.element
        )
        
        return result
        
    except FuryException as e:
        logger.error(f"Generation failed: {e.message}")
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "ok": 0,
                "message": {
                    "code": e.code,
                    "text": e.message
                }
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": 0,
                "message": {
                    "code": "INTERNAL_ERROR",
                    "text": f"Internal server error: {str(e)}"
                }
            }
        )

