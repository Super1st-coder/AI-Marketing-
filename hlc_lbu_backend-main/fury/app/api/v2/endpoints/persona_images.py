"""POST /persona-images — creates a persona image job via Celery.

Job state is stored entirely in the Celery result backend (Redis).
Use GET /jobs/{task_id} to poll status and get the final result.

For local development without Celery/Redis, use POST /persona-images/run-local.
"""
import uuid
from fastapi import APIRouter, HTTPException
from schemas.persona_schemas import PersonaImageCreate, PersonaImageJobResponse
from services.persona_job_runner_service import (
    run_persona_pipeline, 
    _run_persona_pipeline, 
    run_edit_persona_main_image_pipeline, 
    _run_edit_persona_main_image_pipeline,
    run_generate_persona_image_variations_pipeline,
    _run_generate_persona_image_variations_pipeline,
)
from core.config import settings

router = APIRouter()


@router.post("", status_code=201, response_model=PersonaImageJobResponse)
async def create_persona_image(body: PersonaImageCreate):
    """Create a new persona image generation job and start the pipeline.

    Returns a task_id. Poll GET /api/v2/jobs/{task_id} for status and result.

    Pipeline steps:
      1. PersonaDataCollector — fetches buyer persona + optional product from Sinergia
      2. PersonaPrompter     — generates master prompt + N variation sub-prompts
      3. NanoBanana          — generates images via Gemini
      4. Upload              — uploads images to Sinergia library (best-effort)
    """
    task = run_persona_pipeline.apply_async(
        kwargs={
            "id_buyer_persona": body.id_buyer_persona,
            "n_variations": body.n_variations,
            "photography_effect": body.photography_effect,
            "id_product": body.id_product,
            "custom_prompt": body.custom_prompt,
        }
    )

    return PersonaImageJobResponse(
        ok=1,
        data={
            "task_id": task.id,
            "id_buyer_persona": body.id_buyer_persona,
            "n_variations": body.n_variations,
            "photography_effect": body.photography_effect,
            "status": "RUNNING",
            "poll_url": f"/api/v2/jobs/{task.id}",
        },
    )


@router.post("/run-local", status_code=200)
async def run_persona_image_local(body: PersonaImageCreate):
    """Run the persona image pipeline INLINE — no Celery, no Redis. Returns result directly.

    DEV-ONLY endpoint. Only available when DEBUG=true.
    Perfect for fast local iteration without spinning up Celery workers.

    Example:
        curl -X POST http://localhost:8000/api/v2/persona-images/run-local \\
          -H 'Content-Type: application/json' \\
          -d '{
            "id_buyer_persona": 103,
            "n_variations": 2,
            "photography_effect": "studio",
            "id_adset": 173
          }'
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

    task_id = str(uuid.uuid4())
    try:
        result = await _run_persona_pipeline(
            task=None,
            task_id=task_id,
            id_buyer_persona=body.id_buyer_persona,
            n_variations=body.n_variations,
            photography_effect=body.photography_effect,
            id_product=body.id_product,
            custom_prompt=body.custom_prompt,
        )
        return {"ok": 1, "data": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/edit/main-image", status_code=201, response_model=PersonaImageJobResponse)
async def edit_persona_main_image(body: PersonaImageCreate):
    """Create a new persona main image editing job and start the pipeline.

    Returns a task_id. Poll GET /api/v2/jobs/{task_id} for status and result.

    Pipeline steps:
      1. DataCollector — fetches buyer persona + product + base image info
      2. NanoBanana2 — edits base image via Gemini with custom_prompt + references
      3. Prompter — analyzes variations and generates descriptive prompts
      4. UploadImages — uploads images to Sinergia library
      5. Result — assembles final result
    """
    task = run_edit_persona_main_image_pipeline.apply_async(
        kwargs={
            "id_buyer_persona": body.id_buyer_persona,
            "n_variations": body.n_variations,
            "photography_effect": body.photography_effect,
            "id_product": body.id_product,
            "custom_prompt": body.custom_prompt,
            "id_base_image": body.id_base_image,
            "reference_images": body.reference_images,
            "visual_style": body.visual_style,
        }
    )

    return PersonaImageJobResponse(
        ok=1,
        data={
            "task_id": task.id,
            "id_buyer_persona": body.id_buyer_persona,
            "n_variations": body.n_variations,
            "photography_effect": body.photography_effect,
            "status": "RUNNING",
            "poll_url": f"/api/v2/jobs/{task.id}",
        },
    )


@router.post("/edit/main-image/run-local", status_code=200)
async def run_edit_persona_main_image_local(body: PersonaImageCreate):
    """Run the edit persona main image pipeline INLINE — no Celery, no Redis. Returns result directly.

    DEV-ONLY endpoint. Only available when DEBUG=true.
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

    task_id = str(uuid.uuid4())
    try:
        result = await _run_edit_persona_main_image_pipeline(
            task=None,
            task_id=task_id,
            id_buyer_persona=body.id_buyer_persona,
            n_variations=body.n_variations,
            photography_effect=body.photography_effect,
            id_product=body.id_product,
            custom_prompt=body.custom_prompt,
            id_base_image=body.id_base_image,
            reference_images=body.reference_images,
        )
        return {"ok": 1, "data": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/edit/variant", status_code=201, response_model=PersonaImageJobResponse)
async def edit_persona_variant(body: PersonaImageCreate):
    """Edit a persona VARIANT image — independent of the main-image editor.

    Same image-to-image edit as /edit/main-image (NanoBanana2 + custom_prompt), but the
    result is saved as a VARIANT attached to ``id_base_image`` (the variant being edited)
    via ``upload_persona_image_variant`` — it does NOT create a new main image.

    Returns a task_id. Poll GET /api/v2/jobs/{task_id} for status and result.
    """
    if not body.id_base_image:
        raise HTTPException(status_code=400, detail="id_base_image (the variant to edit) is required")

    task = run_edit_persona_main_image_pipeline.apply_async(
        kwargs={
            "id_buyer_persona": body.id_buyer_persona,
            "n_variations": body.n_variations,
            "photography_effect": body.photography_effect,
            "id_product": body.id_product,
            "custom_prompt": body.custom_prompt,
            "id_base_image": body.id_base_image,
            "reference_images": body.reference_images,
            "save_as": "variant",
            "label": body.label,
            "visual_style": body.visual_style,
        }
    )

    return PersonaImageJobResponse(
        ok=1,
        data={
            "task_id": task.id,
            "id_buyer_persona": body.id_buyer_persona,
            "n_variations": body.n_variations,
            "photography_effect": body.photography_effect,
            "status": "RUNNING",
            "poll_url": f"/api/v2/jobs/{task.id}",
        },
    )


@router.post("/main-image/variant/generate", status_code=201, response_model=PersonaImageJobResponse)
async def generate_persona_image_variants(body: PersonaImageCreate):
    """Create a new persona image variants generation job and start the pipeline.

    Generates 5 visual variants: Frontal, Side Face, Expression, Full Body, Outfit.
    Returns a task_id. Poll GET /api/v2/jobs/{task_id} for status and result.

    Pipeline steps:
      1. DataCollector — fetches buyer persona + base image info
      2. Prompt Generation — generates 5 variant prompts
      3. Image Generation — generates variations via NanoBanana2
      4. UploadImages — uploads images to Sinergia library
      5. Result — assembles final result
    """
    if not body.id_base_image:
        raise HTTPException(status_code=400, detail="id_base_image is required")

    task = run_generate_persona_image_variations_pipeline.apply_async(
        kwargs={
            "id_buyer_persona": body.id_buyer_persona,
            "id_base_image": body.id_base_image,
            "id_product": body.id_product,
        }
    )

    return PersonaImageJobResponse(
        ok=1,
        data={
            "task_id": task.id,
            "id_buyer_persona": body.id_buyer_persona,
            "id_base_image": body.id_base_image,
            "id_product": body.id_product,
            "status": "RUNNING",
            "poll_url": f"/api/v2/jobs/{task.id}",
        },
    )


@router.post("/main-image/variant/generate/run-local", status_code=200)
async def run_generate_persona_image_variants_local(body: PersonaImageCreate):
    """Run the persona image variants pipeline INLINE — no Celery, no Redis. Returns result directly.

    DEV-ONLY endpoint. Only available when DEBUG=true.
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

    if not body.id_base_image:
        raise HTTPException(status_code=400, detail="id_base_image is required")

    task_id = str(uuid.uuid4())
    try:
        result = await _run_generate_persona_image_variations_pipeline(
            task=None,
            task_id=task_id,
            id_buyer_persona=body.id_buyer_persona,
            id_base_image=body.id_base_image,
            id_product=body.id_product,
        )
        return {"ok": 1, "data": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
