"""
Mock Tools for Agent Engine Shadow Testing.
These tools are used to prevent the cloud agent from generating actual images
and creating duplicate records in Abyssale during the parallel testing phase.
"""
from typing import Any, List, Dict
import uuid

async def mock_nano_banana_generation(image_prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Mock the image generation tool.
    Returns fake image URLs instead of calling the expensive Nano Banana model.
    """
    results = []
    for prompt in image_prompts:
        results.append({
            "plan_id": prompt.get("plan_id", "mock_plan_id"),
            "image_url": "https://mock-image-bucket.s3.amazonaws.com/shadow-test-placeholder.png",
            "prompt_used": prompt.get("description", "mock prompt")
        })
    return results


async def mock_abyssale_submission(
    job_id: str, 
    copies: List[Dict[str, Any]], 
    generated_images: List[Dict[str, Any]], 
    template_ids: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Mock the Abyssale template mapper.
    Returns a fake batch ID instead of triggering actual Abyssale generation.
    """
    return {
        "abyssale_batch_id": f"mock-batch-{uuid.uuid4().hex[:8]}",
        "status": "WAITING_ABYSSALE_MOCKED",
        "job_id": job_id
    }
