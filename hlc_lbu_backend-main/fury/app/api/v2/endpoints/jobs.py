"""GET /jobs/{task_id} — poll Celery task state and result. No DB tables needed."""
import traceback
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from celery.result import AsyncResult
from services.celery_app import celery_app
from core.auth import verify_internal_api_key
from core.config import settings
from core.validation import AgentValidationError
from schemas.pipeline_schemas import AD_VARIANT_IMAGE_EDIT_RESULT_KEYS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{task_id}")
async def get_job_status(
    task_id: str,
    _: str = Depends(verify_internal_api_key),
):
    """Poll the pipeline job status and retrieve the final result.

    Status lifecycle:
        PENDING  → queued, worker not yet picked up
        STARTED  → worker started
        PROGRESS → pipeline running (meta.step shows current step)
        SUCCESS  → done — result has proposals, renders, validation_report
        FAILURE  → failed — result has error + traceback
    """
    result: AsyncResult = celery_app.AsyncResult(task_id)

    state = result.state
    info = result.info

    if state == "FAILURE":
        if isinstance(info, AgentValidationError):
            error_detail = info.to_dict()
        else:
            error_detail = str(info)
    
        tb = None
        if hasattr(info, "__traceback__"):
            tb = "".join(traceback.format_tb(info.__traceback__))

        if isinstance(info, dict):
            error_detail = info.get("error", str(info))
            tb = info.get("traceback")

        return {
            "ok": 0,
            "data": {
                "task_id": task_id,
                "status": "FAILED",
                "error": error_detail,
                "traceback": tb if settings.DEBUG else None,
            },
        }

    if state == "SUCCESS":
        payload: Any = "Ok"
        if isinstance(info, dict) and frozenset(info) == AD_VARIANT_IMAGE_EDIT_RESULT_KEYS:
            payload = info  # Req 10.7 — only the ad-variant image-edit pipeline
        return {
            "ok": 1,
            "data": {
                "task_id": task_id,
                "status": "DONE",
                "result": payload,
            },
        }

    # PENDING / STARTED / PROGRESS
    return {
        "ok": 1,
        "data": {
            "task_id": task_id,
            "status": state,
            "meta": info if isinstance(info, dict) else {"raw": str(info)},
        },
    }
