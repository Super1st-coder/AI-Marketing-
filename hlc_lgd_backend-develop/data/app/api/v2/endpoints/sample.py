from fastapi import APIRouter, Depends, HTTPException, status
from schemas.sample_schemas import SampleRequest, SampleResponse
from services.sample_service import SampleService
# from core.auth import verify_internal_api_key

router = APIRouter()

@router.post(
    "/process",
    response_model=SampleResponse,
    summary="Process a sample request",
    description="This is a sample endpoint demonstrating the standard flow of the framework.",
    # dependencies=[Depends(verify_internal_api_key)] # Uncomment to require authentication
)
async def process_sample(request: SampleRequest):
    try:
        response = await SampleService.process_sample(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the sample: {str(e)}"
        )
