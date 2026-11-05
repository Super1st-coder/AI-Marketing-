from fastapi import APIRouter, HTTPException
from schemas.llm_schemas import HypothesisRequest, HypothesisResponse
from services.llm_service import LLMService

router = APIRouter()

@router.post("/extract-hypothesis-variables", response_model=HypothesisResponse)
async def extract_hypothesis_variables(request: HypothesisRequest):
    """
    Extracts structured marketing variables from a free-text marketing hypothesis
    using OpenAI's structured outputs.
    """
    try:
        extracted_data = await LLMService.extract_marketing_hypothesis_variables(request.instruction)
        return extracted_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
