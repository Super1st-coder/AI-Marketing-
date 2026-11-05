"""POST /variants — creates a variant job via Celery. No DB tables needed.

Job state is stored entirely in the Celery result backend (Redis).
Use GET /jobs/{task_id} to poll status and get the final result.

For local development without Celery/Redis, use POST /variants/run-local.
"""
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from schemas.pipeline_schemas import (
    VariantCreate,
    VariantJobResponse,
    AdVariantImageEditCreate,
    AdVariantImageEditJobResponse,
    AdVariantImageEditJobData,
)
# Import task directly so it's registered in this process (avoids NotRegistered on Redis backend)
from services.job_runner_service import run_pipeline_phase1, _run_phase1
# Edit pipeline is referenced via the module (attribute lookup at call time) so
# tests can patch `run_edit_ad_variant_image_pipeline.apply_async` and the coroutine.
from services import job_runner_service
from core.config import settings
from core.auth import verify_internal_api_key
from core.exceptions import FuryException, EditJobEnqueueError, EditPipelineInternalError
from core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("", status_code=201, response_model=VariantJobResponse)
async def create_variant(
    body: VariantCreate,
    _: str = Depends(verify_internal_api_key),
):
    """Create a new ad variant job and immediately start the 7-agent pipeline.

    Returns a task_id. Poll GET /api/v2/jobs/{task_id} for status and result.
    """
    task = run_pipeline_phase1.apply_async(
        kwargs={
            "id_adset": body.id_adset,
            "n_variants": body.n_variants,
            "project_id": body.project_id,
            "id_ad": body.id_ad,
            "custom_prompt": body.custom_prompt,
            "add_variant": body.add_variant,
            "id_variant": body.id_variant,
        }
    )

    return VariantJobResponse(
        ok=1,
        data={
            "variant_job_id": task.id,
            "id_adset": body.id_adset,
            "n_variants": body.n_variants,
            "status": "RUNNING",
            "poll_url": f"/api/v2/jobs/{task.id}",
        },
    )


@router.post("/run-local", status_code=200)
async def run_variant_local(
    body: VariantCreate,
    _: str = Depends(verify_internal_api_key),
):
    """Run the pipeline INLINE — no Celery, no Redis. Returns result directly.

    DEV-ONLY endpoint. Only available when DEBUG=true.
    Perfect for fast local iteration without spinning up Celery workers.

    Example:
        curl -X POST http://localhost:8000/api/v2/variants/run-local \\
          -H 'Content-Type: application/json' \\
          -d '{"id_adset": 295, "n_variants": 1}'
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

    task_id = str(uuid.uuid4())
    try:
        result = await _run_phase1(
            task=None,
            task_id=task_id,
            id_adset=body.id_adset,
            n_variants=body.n_variants,
            project_id=body.project_id,
            id_ad=body.id_ad,
            custom_prompt=body.custom_prompt,
            add_variant=body.add_variant,
            id_variant=body.id_variant,
        )
    except Exception as exc:
        # P9: only the exception class name; str(exc) may leak URLs or credentials.
        logger.error(f"[{task_id}] run-local variants failed: {type(exc).__name__}")
        raise HTTPException(status_code=500, detail=type(exc).__name__)
    return {"ok": 1, "data": result}


@router.post("/image/edit", status_code=201, response_model=AdVariantImageEditJobResponse)
async def create_ad_variant_image_edit(
    body: AdVariantImageEditCreate,
    _: str = Depends(verify_internal_api_key),
) -> AdVariantImageEditJobResponse:
    """Enqueue the edit of a variant's base image (Req 2).

    Only enqueues the Celery task; Sinergia, NanoBanana2 and the agent are never
    invoked inside this request. Poll GET /api/v2/jobs/{task_id} for the result.
    """
    kwargs = body.model_dump(mode="json")  # 10 keys; expand_zoom_option -> str | None
    try:
        task = job_runner_service.run_edit_ad_variant_image_pipeline.apply_async(kwargs=kwargs)
    except Exception as exc:
        logger.error(f"[enqueue] edit job enqueue failed: {type(exc).__name__}")
        raise EditJobEnqueueError(
            "No se pudo encolar el job de edición",
            details={"variant_id": body.variant_id, "id_base_image": body.id_base_image},
        )

    task_id = str(task.id)
    return AdVariantImageEditJobResponse(
        ok=1,
        data=AdVariantImageEditJobData(
            edit_job_id=task_id,
            status="RUNNING",
            poll_url=f"/api/v2/jobs/{task_id}",
        ),
    )


@router.post("/image/edit/run-local", status_code=200)
async def run_ad_variant_image_edit_local(
    body: AdVariantImageEditCreate,
    _: str = Depends(verify_internal_api_key),
) -> dict[str, Any]:
    """Run the edit pipeline INLINE — no Celery, no Redis (Req 3).

    DEV-ONLY endpoint. Only available when DEBUG=true (404 otherwise).
    FuryException is re-raised so `fury_exception_handler` renders it (Req 12.2);
    any other exception becomes EditPipelineInternalError without str(exc) (Req 12.3).
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")

    task_id = str(uuid.uuid4())
    try:
        result = await job_runner_service._run_edit_ad_variant_image_pipeline(
            task=None,
            task_id=task_id,
            **body.model_dump(mode="json"),
        )
    except FuryException:
        raise
    except Exception as exc:
        # No traceback, no str(exc): it could contain signed URLs or credentials.
        logger.error(f"[{task_id}] run-local edit pipeline failed: {type(exc).__name__}")
        raise EditPipelineInternalError(
            "Error interno ejecutando el pipeline de edición",
            details={"task_id": task_id, "error_type": type(exc).__name__},
        )
    return {"ok": 1, "data": result}
