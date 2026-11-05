from schemas.sample_schemas import SampleRequest, SampleResponse
from core.logging import get_logger

logger = get_logger(__name__)

class SampleService:
    @staticmethod
    async def process_sample(request: SampleRequest) -> SampleResponse:
        logger.info(f"Processing sample request for name: {request.name}")
        
        # Add your business logic here
        processed_value = request.value * 2
        
        return SampleResponse(
            message=f"Hello, {request.name}! Your request was processed successfully.",
            processed_value=processed_value
        )
