"""Webhooks — Abyssale and AI Expansion callbacks.

Uses Redis directly (via Celery backend) for batch_id→task_id lookup.
No DB tables required.
"""
import json
from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult

from schemas.pipeline_schemas import AbyssaleWebhookPayload, AIExpansionWebhookPayload
from core.config import settings
from services.celery_app import celery_app

router = APIRouter()


def _redis():
    """Return a Redis client using the Celery backend connection."""
    import redis
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def _get_task_id_for_batch(batch_id: str, source: str) -> str | None:
    r = _redis()
    return r.get(f"fury:webhook:{source}:{batch_id}")


def _mark_received(batch_id: str, source: str):
    r = _redis()
    r.set(f"fury:webhook:{source}:{batch_id}", "received", ex=86400)


# ---------------------------------------------------------------------------
# Abyssale webhook — renders 4:5 ready
# ---------------------------------------------------------------------------

@router.post("/abyssale/{secret}")
async def abyssale_webhook(
    secret: str,
    payload: AbyssaleWebhookPayload,
):
    """Receive Abyssale render completion callback.

    Path param `secret` must match settings.ABYSSALE_WEBHOOK_SECRET.
    Deduplication via Redis key fury:webhook:abyssale:{batch_id}.
    On success dispatches AI Expansion as a new Celery task.
    """
    if secret != settings.ABYSSALE_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    # Dedup
    r = _redis()
    dedup_key = f"fury:webhook:abyssale:{payload.batch_id}"
    if r.get(dedup_key) == "done":
        return {"ok": 1, "status": "duplicate_ignored"}
    r.set(dedup_key, "done", ex=86400)

    if payload.status == "failed":
        # Find task and update meta via Celery
        task_id = _get_task_id_for_batch(payload.batch_id, "task")
        if task_id:
            celery_app.send_task(
                "services.job_runner_service.mark_job_failed",
                kwargs={"task_id": task_id, "reason": "abyssale_render_failed"},
            )
        return {"ok": 1, "status": "job_failed"}

    # Find the original Celery task_id for this batch
    task_id = _get_task_id_for_batch(payload.batch_id, "task")
    if not task_id:
        raise HTTPException(status_code=404, detail="No task found for batch_id")

    # Dispatch AI Expansion as next Celery step
    celery_app.send_task(
        "services.job_runner_service.trigger_ai_expansion",
        kwargs={"task_id": task_id, "renders": payload.renders},
    )

    return {"ok": 1, "status": "expansion_triggered", "task_id": task_id}


# ---------------------------------------------------------------------------
# AI Expansion webhook — 1:1 and 9:16 formats ready
# ---------------------------------------------------------------------------

@router.post("/expansion/{secret}")
async def ai_expansion_webhook(
    secret: str,
    payload: AIExpansionWebhookPayload,
):
    """Receive AI Expansion callback with 1:1 and 9:16 format renders.

    Finalizes the Celery task result with all renders.
    The client polls GET /jobs/{task_id} to get the complete result.
    """
    if secret != settings.ABYSSALE_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    # Dedup
    r = _redis()
    dedup_key = f"fury:webhook:expansion:{payload.batch_id}"
    if r.get(dedup_key) == "done":
        return {"ok": 1, "status": "duplicate_ignored"}
    r.set(dedup_key, "done", ex=86400)

    task_id = _get_task_id_for_batch(payload.batch_id, "task")
    if not task_id:
        raise HTTPException(status_code=404, detail="No task found for batch_id")

    # Store expanded renders in Redis so GET /jobs/{task_id} can return them
    r.set(
        f"fury:result:{task_id}:expanded_renders",
        json.dumps(payload.expanded_renders),
        ex=86400 * 7,
    )

    # Finalize result in Celery backend
    celery_app.send_task(
        "services.job_runner_service.finalize_job",
        kwargs={"task_id": task_id, "expanded_renders": payload.expanded_renders},
    )

    return {"ok": 1, "status": "done", "task_id": task_id}
