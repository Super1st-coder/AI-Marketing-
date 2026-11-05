"""Abyssale tools — build payload, post async generation, save WAITING status."""
import uuid
from typing import Any
import httpx
from core.config import settings
from core.logging import get_logger

if settings.USE_MOCK_SINERGIA:
    from agents.tools.mock_sinergia import (
        update_ad_channel_with_batch_id,
    )
else:
    from agents.tools.campaign_tools import (
        update_ad_channel_with_batch_id,
    )

logger = get_logger(__name__)


def build_abyssale_payload(
    creative_content: list[dict],
    template_id: str,
    format_ratio: str,
) -> dict[str, Any]:
    """Map creative content (copy + images) into Abyssale's batch generation payload.

    Overlay text is already fitted to each element's REAL max_char upstream, in
    _save_ads_programmatically (which has the template definition loaded), so the
    copy objects reaching here carry text that already respects the template's
    per-element limits. No char-limit guessing happens here.

    Args:
        creative_content: List of {plan, copy, image_url} dicts from _merge_creative.
        template_id: Abyssale template identifier.
        format_ratio: Target format — "4:5", "1:1", or "9:16". Use "4:5" if unsure.

    Returns:
        Dict with Abyssale-compatible payload ready to POST.
    """
    elements_batch = []
    for item in creative_content:
        if "error" in item:
            logger.warning(f"Skipping plan with error: {item['error']}")
            continue

        copy = item.get("copy", {})
        ad_channel = item.get("ad_channel", {})
        # Text layers first (last repeated element_id wins, as before). Images
        # never overwrite a text layer of the same entry, regardless of list
        # order (adset-creative-diversity P15 / D27, Req 15.11; both paths).
        text_layers = {}
        for a_element in copy.get('template_elements', []):
            text_layers[a_element.get('element_id')] = {'payload': a_element.get('text', "")}
        elements = dict(text_layers)

        img = item.get("image", {})
        img_ids = []
        for a_image in img.get('image_prompts', []):
            if not a_image.get('image_url'):
                continue
            element_id = a_image.get('element_id')
            if element_id in text_layers:
                # Never log the image URL or its content (Req 15.13).
                logger.warning(
                    f"build_abyssale_payload: image skipped for text layer "
                    f"template_id={copy.get('template_id', '')} element_id={element_id!r}"
                )
                continue
            elements[element_id] = {'image_encoded': a_image.get('image_url')}
            img_ids.append({'image_id': a_image.get('image_id', ''), 'image_name': a_image.get('element_id', '')})

        elements_batch.append({
            "template_id": copy.get('template_id', ''),
            "format": format_ratio,
            "layers": elements,
            "metadata": {"plan_id": item.get("plan", {}).get("id", "")},
            "template_format_name": 'instagram-portrait',
            "ad_channel_id": ad_channel.get("ad_id"),  # For tracking in Abyssale
            "image_ids": img_ids,  # Custom field to track which images are used
        })

    payload = {
        "elements": elements_batch,
        "callback_url": settings.ABYSSALE_WEBHOOK_CALLBACK_URL or "",
        "async": True,
    }
    logger.info(f"Built Abyssale payload with {len(elements_batch)} elements")
    return {"ok": True, "payload": payload}


async def post_to_abyssale_and_wait(
    job_id: str,
    abyssale_payload: dict,
    id_adset: int,
    ad_id: int,
) -> dict[str, Any]:
    """POST the batch payload to Abyssale and update the job status to WAITING_ABYSSALE.

    In dev mode (no ABYSSALE_API_KEY), returns the payload JSON directly
    without making any HTTP call — so you can inspect what would be sent.

    Args:
        job_id: Current pipeline job ID.
        abyssale_payload: The payload dict from build_abyssale_payload.

    Returns:
        Dict with Abyssale batch_id, status, and (in dev mode) the payload preview.
    """

    if not settings.ABYSSALE_API_KEY or not settings.ABYSSALE_WEBHOOK_CALLBACK_URL:
        mock_batch_id = f"mock-batch-{uuid.uuid4().hex[:8]}"
        logger.warning(
            f"[DEV] ABYSSALE_API_KEY not set — skipping real submission. "
            f"Returning payload preview. mock_batch_id={mock_batch_id}"
        )
        return {
            "ok": True,
            "status": "WAITING_ABYSSALE",
            "batch_id": mock_batch_id,
            "message": "[DEV] Mock — payload below is what would be sent to Abyssale.",
            "abyssale_payload_preview": abyssale_payload or {},
            "abyssale_response": [],
        }
    
    batch_ids = []
    abyssale_response = []
   
    for item in abyssale_payload.get("elements", []):
        batch_id = None
        try:
            template_id = item.get("template_id", "")
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.ABYSSALE_BASE_URL}/async/banner-builder/{template_id}/generate",
                    headers={
                        "x-api-key": settings.ABYSSALE_API_KEY.strip(),
                        "Content-Type": "application/json",
                    },
                    json={'elements': item.get("layers", {}), 'template_format_names': [], 'callback_url': settings.ABYSSALE_WEBHOOK_CALLBACK_URL},
                )

                response.raise_for_status()
                result = response.json()
                abyssale_response.append(result)

            batch_id = result.get("generation_request_id")
            # Actualizar ad-channel con generation_request_id para correlación futura
            logger.info(f"Updating ad_channel with batch_id={batch_id} for ad_channel_id={item.get('ad_channel_id')}")
            await update_ad_channel_with_batch_id(item.get('ad_channel_id'), batch_id, item.get('image_ids', []))
            logger.info(f"Abyssale batch submitted: batch_id={batch_id} for job={job_id}")
        except Exception as e:
            logger.error(f"Error submitting to Abyssale: {str(e)}")
            logger.error(f"Response content: {response.text if 'response' in locals() else 'N/A'}")
            if settings.DEBUG:
                import os
                out_dir = "/tmp/fury_errors"
                os.makedirs(out_dir, exist_ok=True)
                path = f"{out_dir}/{template_id[:12]}_error.log"
                with open(path, "w") as f:
                    f.write(response.text)
            continue

        if batch_id:
            batch_ids.append(batch_id)
            try:
                import redis as redis_lib
                r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
                r.set(f"fury:webhook:task:{batch_id}", job_id, ex=86400 * 7)
                logger.info(f"Registered fury:webhook:task:{batch_id} → {job_id}")
            except Exception as redis_err:
                logger.warning(f"Could not store batch_id in Redis (non-fatal): {redis_err}")

    return {
        "ok": True,
        "status": "WAITING_ABYSSALE",
        "batch_id": batch_ids,
        "message": "Abyssale render started. Pipeline paused until webhook arrives.",
        "abyssale_response": abyssale_response or [],
    }
