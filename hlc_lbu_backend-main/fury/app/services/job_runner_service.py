"""Celery tasks for the Fury 7-agent pipeline.

State is stored entirely in the Celery result backend (Redis).
No DB tables. No asyncpg.
"""
import asyncio
import copy
import functools
import json
import math
import os
import re
import traceback
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx
from celery.exceptions import SoftTimeLimitExceeded

from core.config import settings
from core.exceptions import AdVariantImageEditError
from core.logging import get_logger
from core.validation import ValidationResult, AgentValidationError
from services.celery_app import celery_app
from services.text_limits import fit_to_limit
from helpers.agent import run_agent as _run_agent

from langfuse import observe

if TYPE_CHECKING:  # type-only: the Diversity_Path imports these lazily (Req 2.4)
    from schemas.territory_schemas import AdDescription
    from services.adset_diversity import AdSlotPlan, CreativePlan, DiversityReport, ImageElements

logger = get_logger(__name__) 


# ---------------------------------------------------------------------------
# Presigned-URL sanitizer
# ---------------------------------------------------------------------------

# Query-string markers that identify a *signed* asset URL (AWS S3 / CloudFront /
# GCS). Their query string carries live, short-lived credentials.
_SIGNED_URL_MARKERS = ("X-Amz-", "Signature=", "GoogleAccessId=", "Key-Pair-Id=")


def _strip_signed_urls(obj: Any) -> Any:
    """Recursively drop the signing query-string from presigned asset URLs.

    Sinergia returns brand assets (logos, product images) as S3 *presigned* URLs
    whose query string carries live AWS credentials — ``X-Amz-Credential``,
    ``X-Amz-Security-Token``, ``X-Amz-Signature``. Those must never reach an LLM
    prompt: (1) it leaks short-lived credentials to a third-party model, and
    (2) the credentials safety-guard's ``\\bcredential`` pattern matches
    ``X-Amz-Credential`` and blocks the whole call — the LLM is skipped and the
    guard's "[SAFETY_GUARD] ... blocked" text fails JSON validation
    (ERR_INVALID_JSON). We keep the object path (still a usable reference) and
    drop everything after '?'.
    """
    if isinstance(obj, dict):
        return {k: _strip_signed_urls(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_signed_urls(v) for v in obj]
    if isinstance(obj, str) and obj.startswith("http") and "?" in obj:
        base, _, query = obj.partition("?")
        if any(marker in query for marker in _SIGNED_URL_MARKERS):
            return base
    return obj


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------

def _redis():
    import redis
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


_CHECKPOINT_TTL = 7200  # 2 horas


def _cp_key(task_id: str, ad_id, step: str) -> str:
    """Redis key for a pipeline step checkpoint."""
    return f"fury:cp:{task_id}:{ad_id}:{step}"


def _store(key: str, value: Any, ex: int = 86400 * 7):
    _redis().set(key, json.dumps(value), ex=ex)


def _load(key: str) -> Any:
    raw = _redis().get(key)
    return json.loads(raw) if raw else None


# ---------------------------------------------------------------------------
# Ad-variant image-edit pipeline — constants & private helpers
# ---------------------------------------------------------------------------
# Used by `_run_edit_ad_variant_image_pipeline` / `run_edit_ad_variant_image_pipeline`
# (fetch_base_image → download → image_editing → prompt_analysis → upload →
#  resolve_urls → done).
# Every helper reaches Redis through the module-level `_load` / `_store` / `_redis`
# so tests can patch `_redis` with an in-memory fake.

# Steps that persist a checkpoint (`download` has none: its output is the binary,
# which only lives in memory and materializes in `image_editing`). `upload` checkpoints
# the library_ids; `resolve_urls` checkpoints the resolved public URLs (Req 11.7).
_EDIT_STEPS: tuple[str, ...] = (
    "fetch_base_image", "image_editing", "prompt_analysis", "upload", "resolve_urls",
)
# PROGRESS steps, always emitted in this order even when skipped (Req 11.11).
_EDIT_PROGRESS_STEPS: tuple[str, ...] = (
    "fetch_base_image", "download", "image_editing", "prompt_analysis", "upload",
    "resolve_urls", "done",
)
_BASE_IMAGE_DOWNLOAD_TIMEOUT_S = 30  # Req 5.1 — domain constant, not a setting
_LIBRARY_INDEX_DELAY_S = 15          # Req 14.1 — Sinergia library indexing delay
_RESOLVE_URL_RETRIES = 3             # Req 14.5 — extra URL_Resolution attempts per image
_RESOLVE_URL_RETRY_DELAY_S = 5       # Req 14.5 — wait between URL_Resolution attempts
# D17, Req 9.12 — Image_Name_Extension stripped from the Variation_Image_Name.
_IMAGE_NAME_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp", ".gif")

# Edit_Sleep (Req 14.2): ALWAYS invoked as `_edit_sleep(...)`, resolved from the
# module at call time and never captured as a parameter default, so tests can
# patch it (`job_runner_service._edit_sleep = fake`) without real waits.
_edit_sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
_REDACT_MAX_CHARS = 300
_IMAGE_PROMPT_MAX_CHARS = 2000  # mirrors ads_validators.AD_VARIANT_IMAGE_PROMPT_MAX_CHARS

_URL_RE = re.compile(r"https?://[^\s'\"<>]+")
_DATA_URI_RE = re.compile(
    r"data:([\w.+-]+/[\w.+-]+);base64,([A-Za-z0-9+/=_-]*?)(?=data:|[^A-Za-z0-9+/=_-]|$)"
)
# Leftover signing parameters outside a full URL (e.g. a truncated query in an
# exception message) — dropped so no credential fragment survives.
_SIGNING_PARAM_RE = re.compile(
    r"(?i:X-Amz-[A-Za-z-]*)(?:=[^&\s'\"<>]*)?"
    r"|(?:Signature|GoogleAccessId|Key-Pair-Id)=[^&\s'\"<>]*"
)


def _redis_errors() -> tuple[type[BaseException], ...]:
    """Exception types that mean "Redis is unavailable" (D8)."""
    errors: tuple[type[BaseException], ...] = (ConnectionError, TimeoutError, OSError)
    try:
        from redis.exceptions import RedisError
        errors = (RedisError, *errors)
    except ImportError:  # pragma: no cover - redis is a runtime dependency
        pass
    return errors


def _edit_cp_load(task, task_id: str, ad_id: int, step: str) -> Any:
    """Load an edit-pipeline checkpoint.

    D8: with `task is None` (run-local, no Redis required) a Redis outage is
    logged and treated as "no checkpoint". Under Celery the error propagates so
    the task retries instead of silently recomputing.
    """
    try:
        return _load(_cp_key(task_id, ad_id, step))
    except _redis_errors() as exc:
        if task is not None:
            raise
        logger.warning(
            f"[{task_id}] checkpoint load skipped step={step}: Redis unavailable "
            f"({type(exc).__name__})"
        )
        return None


def _edit_cp_store(task, task_id: str, ad_id: int, step: str, value: Any) -> None:
    """`_store(_cp_key(task_id, ad_id, step), value, ex=_CHECKPOINT_TTL)`. See D8."""
    try:
        _store(_cp_key(task_id, ad_id, step), value, ex=_CHECKPOINT_TTL)
    except _redis_errors() as exc:
        if task is not None:
            raise
        logger.warning(
            f"[{task_id}] checkpoint store skipped step={step}: Redis unavailable "
            f"({type(exc).__name__})"
        )


def _redact_text(text: Any) -> str:
    """Sanitize free text (exception messages, causes) before logging or `details`.

    - embedded http(s) URLs → `_strip_signed_urls(url)` (drops the signing query)
    - `data:<mime>;base64,<...>` → `data:<mime>;base64,<redacted N chars>`
    - values of SINERGIA_SERVICE_API_KEY / FURY_INTERNAL_API_KEY → `***`
    - truncated to 300 characters
    httpx error messages embed the full request URL, which may be presigned.
    """
    out = "" if text is None else str(text)
    out = _DATA_URI_RE.sub(
        lambda m: f"data:{m.group(1)};base64,<redacted {len(m.group(2))} chars>", out
    )
    out = _URL_RE.sub(lambda m: _strip_signed_urls(m.group(0)), out)
    out = _SIGNING_PARAM_RE.sub("[redacted]", out)
    for secret in (settings.SINERGIA_SERVICE_API_KEY, settings.FURY_INTERNAL_API_KEY):
        if isinstance(secret, str) and secret:
            out = out.replace(secret, "***")
    return out[:_REDACT_MAX_CHARS]


class _DownloadRejected(Exception):
    """The base-image download returned an unusable response (non-2xx, empty
    body or non-image Content-Type). `cause` is already sanitized."""

    def __init__(self, cause: str):
        super().__init__(cause)
        self.cause = cause


async def _download_base_image(
    url: str,
    task_id: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[bytes, str]:
    """Download the Base_Image binary (Req 5.1, 5.2, 5.6). One attempt per call.

    Accepts 2xx ∧ body ≥ 1 byte ∧ (Content-Type absent ∨ starts with `image/`).
    MIME = Content-Type without parameters, lower-cased; `image/png` if absent.
    Raises `_DownloadRejected(cause)` for unusable responses; transport errors
    and timeouts (httpx.HTTPError) propagate after being logged. `transport` is
    a test seam (httpx.MockTransport); production leaves it None.
    """
    safe_url = _strip_signed_urls(url)
    try:
        async with httpx.AsyncClient(
            timeout=_BASE_IMAGE_DOWNLOAD_TIMEOUT_S,
            follow_redirects=True,
            transport=transport,
        ) as client:
            response = await client.get(url)
    except Exception as exc:
        logger.warning(
            f"[{task_id}] download url={safe_url} failed: "
            f"{type(exc).__name__}: {_redact_text(exc)}"
        )
        raise

    body = response.content
    content_type = response.headers.get("content-type")
    mime = content_type.split(";", 1)[0].strip().lower() if content_type is not None else None

    cause: str | None = None
    if not 200 <= response.status_code < 300:
        cause = f"HTTP {response.status_code}"
    elif len(body) < 1:
        cause = "empty body (0 bytes)"
    elif mime is not None and not mime.startswith("image/"):
        cause = f"unexpected Content-Type {_redact_text(content_type)!r}"

    if cause is not None:
        logger.warning(f"[{task_id}] download url={safe_url} rejected: {cause}")
        raise _DownloadRejected(cause)

    mime = mime or "image/png"
    logger.info(f"[{task_id}] download url={safe_url} → {len(body)} bytes {mime}")
    return body, mime


async def _resolve_variation_url(
    get_ad_variant_image,
    *,
    task_id: str,
    brand_id: int,
    campaign_id: int,
    ad_id: int,
    channel_id: int,
    variant_id: int,
    image_name: str,
    image_id: str,
) -> tuple[str | None, int, str]:
    """URL_Resolution with bounded retries (Req 14.3–14.5, 12.10).

    Up to 1 + _RESOLVE_URL_RETRIES queries; `await _edit_sleep(_RESOLVE_URL_RETRY_DELAY_S)`
    before each repetition (not after the last one). Accepts only a dict with
    `id == image_id` and a `url` str that is non-empty after strip.

    Returns `(url unmodified | None, queries made, last cause sanitized)`; the
    cause is "" on success. Never raises for dependency failures: exceptions of
    `get_ad_variant_image` become the cause. Only Celery's SoftTimeLimitExceeded
    (and BaseException such as CancelledError) propagate, so the task-level
    time limit still triggers the retry path.
    """
    max_attempts = 1 + _RESOLVE_URL_RETRIES
    cause = ""
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            await _edit_sleep(_RESOLVE_URL_RETRY_DELAY_S)
        try:
            resp = await get_ad_variant_image(
                brand_id, campaign_id, ad_id, channel_id, variant_id, image_name, image_id,
            )
        except SoftTimeLimitExceeded:
            raise
        except Exception as exc:
            cause = _redact_text(f"{type(exc).__name__}: {exc}")
        else:
            if not isinstance(resp, dict):
                cause = f"unexpected response type {type(resp).__name__}"
            elif resp.get("id") != image_id:
                cause = _redact_text(
                    f"id mismatch: expected={image_id} received={resp.get('id')}"
                )
            else:
                url = resp.get("url")
                if isinstance(url, str) and url.strip():
                    return url, attempt, ""
                cause = "missing or blank url"
        logger.warning(
            f"[{task_id}] resolve_urls id={_redact_text(image_id)} "
            f"attempt {attempt}/{max_attempts} rejected: {cause}"
        )
    return None, max_attempts, cause


def _to_data_uri(image_b64: str, mime_type: str) -> str:
    """Rebuild the data-URI in memory (checkpoints only hold raw base64, D5)."""
    return f"data:{mime_type};base64,{image_b64}"


def _variation_image_name(image_name: str, index: int) -> str:
    """Variation_Image_Name (Req 9.5, 9.12, 9.13, D17).

    Strips at most ONE trailing extension from _IMAGE_NAME_EXTENSIONS
    (case-insensitive) and appends f"_{index}" (1-based). Sinergia then adds
    the extension derived from the real MIME type, so the final file has a
    single extension. Any other dotted suffix is preserved. If the stem would
    be empty (image_name == ".png"), nothing is stripped.

    'banner.png', 1    → 'banner_1'      (final file 'banner_1.png')
    'banner.JPG', 2    → 'banner_2'
    'banner.jpg', 1    → 'banner_1'      (with MIME image/png → 'banner_1.png')
    'banner', 3        → 'banner_3'
    'promo v1.2', 1    → 'promo v1.2_1'
    'photo.tar.png', 1 → 'photo.tar_1'
    '.png', 1          → '.png_1'        (empty stem: name kept as is)
    """
    lowered = image_name.lower()
    for ext in _IMAGE_NAME_EXTENSIONS:
        if lowered.endswith(ext) and len(image_name) > len(ext):
            return f"{image_name[: -len(ext)]}_{index}"
    return f"{image_name}_{index}"


def _extract_image_prompt(raw: Any) -> str | None:
    """`image_prompt` from the Variant_Prompter output (JSON text or parsed dict).

    `run_agent` may return raw text or `ValidationResult.data`; both go through
    `_parse_json_response`. Returns the stripped prompt if it is a non-empty str
    of at most 2000 characters, otherwise None (→ fallback to Edit_Instruction).
    """
    if not isinstance(raw, (str, dict)):
        return None
    parsed = _parse_json_response(raw)
    if not isinstance(parsed, dict):
        return None
    prompt = parsed.get("image_prompt")
    if not isinstance(prompt, str):
        return None
    prompt = prompt.strip()
    if not prompt or len(prompt) > _IMAGE_PROMPT_MAX_CHARS:
        return None
    return prompt


def _is_retryable_edit_error(exc: BaseException) -> bool:
    """False only for AdVariantImageEditError with retryable=False. Anything else
    (incl. SoftTimeLimitExceeded or Redis errors) is retryable, as in
    run_pipeline_phase1."""
    return not (isinstance(exc, AdVariantImageEditError) and not exc.retryable)


def _progress(task, task_id: str, step: str, detail: str = "") -> None:
    """PROGRESS update `{"step", "detail"}` (Celery only) + `[{task_id}]` log line."""
    if task is not None:
        task.update_state(state="PROGRESS", meta={"step": step, "detail": detail})
    logger.info(f"[{task_id}] → {step} {detail}")


def _edit_error_details(
    task_id: str, id_base_image: str, step: str, cause: Any = None, **extra: Any
) -> dict[str, Any]:
    """`details` for edit-pipeline errors: task_id, id_base_image, step (+ sanitized cause)."""
    details: dict[str, Any] = {"task_id": task_id, "id_base_image": id_base_image, "step": step}
    if cause is not None:
        details["cause"] = _redact_text(cause)
    details.update(extra)
    return details


# ---------------------------------------------------------------------------
# Ad-variant image-edit pipeline — coroutine
# ---------------------------------------------------------------------------

@observe(name="fury.ad_variant_image_edit_pipeline")
async def _run_edit_ad_variant_image_pipeline(
    task,
    task_id: str,
    brand_id: int,
    campaign_id: int,
    ad_id: int,
    channel_id: int,
    variant_id: int,
    image_name: str,
    id_base_image: str,
    n_variations: int,
    custom_prompt: str | None = None,
    expand_zoom_option: str | None = None,
) -> dict[str, Any]:
    """Edit the base image of an ad variant into N registered variations.

    Code-driven pipeline with Redis checkpoints (no orchestrator LLM):
    fetch_base_image → download → image_editing → prompt_analysis → upload →
    resolve_urls → done.

    `upload` registers each variation in the Sinergia library and checkpoints
    only `{"id", "prompt"}`. `resolve_urls` then waits `_LIBRARY_INDEX_DELAY_S`
    once (Edit_Sleep, also when resuming from the `upload` checkpoint) and
    resolves each Uploaded_Image's public URL sequentially with
    `_resolve_variation_url`; unresolved images are skipped, and if none
    resolves it raises the retryable `VariationUrlResolutionError` keeping the
    `upload` checkpoint (no re-upload on retry). Otherwise it checkpoints the
    Registered_Variants (URLs stripped of signatures); a retry with that
    checkpoint skips the sleep and every URL_Resolution.
    Called by the Celery task `run_edit_ad_variant_image_pipeline` and inline by
    `/variants/image/edit/run-local` (`task=None`).

    Returns `AdVariantImageEditResult(...).model_dump(mode="json")`.
    Raises `AdVariantImageEditError` subclasses (see core/exceptions.py).
    """
    # Lazy imports (Req 11.12): read module attributes at call time.
    from agents.ad_variant_image_prompter_agent import make_ad_variant_image_prompter_agent
    from agents.nano_banana_agent import edit_image_variations
    from core.exceptions import (
        BaseImageDownloadError,
        BaseImageFetchError,
        BaseImageMismatchError,
        BaseImageUrlMissingError,
        ImageEditingFailedError,
        VariationUploadFailedError,
        VariationUrlResolutionError,
    )
    from schemas.pipeline_schemas import AdVariantImageEditResult
    from services.ads_validators import validate_ad_variant_image_prompter_response
    from services.edit_instruction import build_edit_instruction
    if settings.USE_MOCK_SINERGIA:
        from agents.tools.mock_sinergia import (
            get_ad_variant_image,
            upload_image_to_library as upload_image_to_library_tool,
        )
    else:
        from agents.tools.campaign_tools import (
            get_ad_variant_image,
            upload_image_to_library as upload_image_to_library_tool,
        )

    # Pure and deterministic → identical on every retry, no checkpoint (Req 6.9).
    edit_instruction = build_edit_instruction(expand_zoom_option, custom_prompt)

    cp_fetch = _edit_cp_load(task, task_id, ad_id, "fetch_base_image")
    cp_editing = _edit_cp_load(task, task_id, ad_id, "image_editing")
    cp_analysis = _edit_cp_load(task, task_id, ad_id, "prompt_analysis")
    cp_upload = _edit_cp_load(task, task_id, ad_id, "upload")
    cp_resolve = _edit_cp_load(task, task_id, ad_id, "resolve_urls")
    # D4: any retry that must download refreshes the signed URL from Sinergia.
    needs_download = (
        cp_editing is None and cp_analysis is None
        and cp_upload is None and cp_resolve is None
    )

    # ── fetch_base_image ────────────────────────────────────────────────────
    live_url: str | None = None
    if needs_download:
        _progress(task, task_id, "fetch_base_image", f"variant={variant_id} base_image={id_base_image}")
        try:
            base = await get_ad_variant_image(
                brand_id, campaign_id, ad_id, channel_id, variant_id, image_name, id_base_image,
            )
        except Exception as exc:
            logger.error(
                f"[{task_id}] fetch_base_image failed: {type(exc).__name__}: {_redact_text(exc)}"
            )
            raise BaseImageFetchError(
                "No se pudo obtener la imagen base de Sinergia",
                details=_edit_error_details(
                    task_id, id_base_image, "fetch_base_image", f"{type(exc).__name__}: {exc}",
                ),
            ) from None
        if not isinstance(base, dict):
            raise BaseImageFetchError(
                "Respuesta inválida al obtener la imagen base",
                details=_edit_error_details(
                    task_id, id_base_image, "fetch_base_image", f"unexpected type {type(base).__name__}",
                ),
            )
        received_id = base.get("id")
        if received_id != id_base_image:
            logger.error(
                f"[{task_id}] base image id mismatch: expected={id_base_image} "
                f"received={_redact_text(received_id)}"
            )
            raise BaseImageMismatchError(
                f"La imagen base devuelta ({_redact_text(received_id)}) no coincide con "
                f"id_base_image ({id_base_image})",
                details=_edit_error_details(
                    task_id, id_base_image, "fetch_base_image", "returned id differs from id_base_image",
                    expected_id=id_base_image, received_id=_redact_text(received_id),
                ),
            )
        raw_url = base.get("url")
        if not isinstance(raw_url, str) or not raw_url.strip():
            logger.error(f"[{task_id}] base image {id_base_image} has no url")
            raise BaseImageUrlMissingError(
                "La imagen base no tiene url",
                details=_edit_error_details(task_id, id_base_image, "download", "missing url"),
            )
        live_url = raw_url.strip()  # fresh signed URL — memory only (D4)
        base_prompt = base.get("prompt") if isinstance(base.get("prompt"), str) else ""
        safe_base = {"id": id_base_image, "url": _strip_signed_urls(live_url), "prompt": base_prompt}
        logger.info(f"[{task_id}] base image fetched: {safe_base}")
        if cp_fetch is None:
            _edit_cp_store(task, task_id, ad_id, "fetch_base_image", safe_base)
    else:
        _progress(task, task_id, "fetch_base_image", "checkpoint")
        if isinstance(cp_fetch, dict) and isinstance(cp_fetch.get("prompt"), str):
            base_prompt = cp_fetch["prompt"]
        else:
            base_prompt = ""
            logger.warning(f"[{task_id}] fetch_base_image checkpoint missing; base prompt unavailable")

    # ── download ────────────────────────────────────────────────────────────
    image_bytes: bytes = b""
    image_mime = "image/png"
    if needs_download:
        _progress(task, task_id, "download", f"url={_strip_signed_urls(live_url)}")
        try:
            # Module global so tests can patch `_download_base_image`.
            image_bytes, image_mime = await _download_base_image(live_url, task_id)
        except _DownloadRejected as exc:
            raise BaseImageDownloadError(
                "No se pudo descargar la imagen base",
                details=_edit_error_details(task_id, id_base_image, "download", exc.cause),
            ) from None
        except Exception as exc:
            raise BaseImageDownloadError(
                "No se pudo descargar la imagen base",
                details=_edit_error_details(
                    task_id, id_base_image, "download", f"{type(exc).__name__}: {exc}",
                ),
            ) from None
    else:
        _progress(task, task_id, "download", "skipped")

    # ── image_editing ───────────────────────────────────────────────────────
    if cp_editing is not None:
        _progress(task, task_id, "image_editing", "checkpoint")
        edited: list[dict[str, Any]] = cp_editing
    elif needs_download:
        _progress(task, task_id, "image_editing", f"n={n_variations} mime={image_mime} bytes={len(image_bytes)}")
        edited = await edit_image_variations(
            image_bytes, image_mime, edit_instruction, n_variations, task_id=task_id,
        )
        if not edited:
            logger.error(f"[{task_id}] image_editing produced 0/{n_variations} variations")
            raise ImageEditingFailedError(
                "NanoBanana2 no generó ninguna variación",
                details=_edit_error_details(
                    task_id, id_base_image, "image_editing", f"0/{n_variations} variations generated",
                ),
            )
        logger.info(f"[{task_id}] image_editing → {len(edited)}/{n_variations} variations")
        _edit_cp_store(task, task_id, ad_id, "image_editing", edited)
    else:
        # Only later checkpoints exist: resume from the latest one.
        _progress(task, task_id, "image_editing", "skipped")
        edited = []

    # ── prompt_analysis ─────────────────────────────────────────────────────
    analyzed: list[dict[str, Any]]
    if cp_resolve is not None:
        # URLs already resolved: nothing left to analyze or upload.
        _progress(task, task_id, "prompt_analysis", "skipped")
        analyzed = []
    elif cp_analysis is not None:
        _progress(task, task_id, "prompt_analysis", "checkpoint")
        analyzed = cp_analysis
    elif cp_upload is None:
        _progress(task, task_id, "prompt_analysis", f"variations={len(edited)}")
        agent = make_ad_variant_image_prompter_agent()
        base_prompt_text = base_prompt or "not available"
        analyzed = []
        for variation in edited:
            index = variation.get("index")
            mime = variation.get("mime_type") or "image/png"
            message = (
                "Describe this edited advertising image.\n"
                f"Edit instruction applied: {edit_instruction}\n"
                f"Base image prompt: {base_prompt_text}\n"
                'Return ONLY a JSON object: {"image_prompt": "<description>"}'
            )
            prompt: str | None = None
            try:
                raw = await _run_agent(
                    agent,
                    f"ad_variant_{variant_id}_edit_{task_id}_v{index}",
                    message,
                    image_data=_to_data_uri(variation.get("image_b64", ""), mime),
                    image_mime_type=mime,
                    validator=validate_ad_variant_image_prompter_response,
                )
                prompt = _extract_image_prompt(raw)
                if prompt is None:
                    logger.warning(f"[{task_id}] prompter v{index} fallback: no usable image_prompt")
            except Exception as exc:
                logger.warning(f"[{task_id}] prompter v{index} fallback: {type(exc).__name__}")
            analyzed.append({
                **variation,
                "prompt": prompt or edit_instruction,
                "prompt_source": "agent" if prompt else "fallback",
            })
        _edit_cp_store(task, task_id, ad_id, "prompt_analysis", analyzed)
    else:
        _progress(task, task_id, "prompt_analysis", "skipped")
        analyzed = []

    # ── upload ──────────────────────────────────────────────────────────────
    # Uploaded_Image = {"id": library_id, "prompt"} — no `url` (Sinergia only
    # returns the id; the URL is resolved in `resolve_urls`, D14).
    uploaded: list[dict[str, str]]
    if cp_resolve is not None:
        _progress(task, task_id, "upload", "skipped")
        uploaded = []
    elif cp_upload is not None:
        # 0 calls to upload_image_to_library_tool → no library duplicates (Req 9.11).
        _progress(task, task_id, "upload", "checkpoint")
        uploaded = cp_upload
    else:
        _progress(task, task_id, "upload", f"variations={len(analyzed)}")
        uploaded = []
        for variation in analyzed:  # sequential on purpose (Req 9.4)
            index = variation.get("index")
            mime = variation.get("mime_type") or "image/png"
            payload = {
                "image_data": _to_data_uri(variation.get("image_b64", ""), mime),
                "image_name": _variation_image_name(image_name, index),
                "mime_type": mime,
                "image_prompt": variation["prompt"],
            }
            try:
                # Returns the library image_id as `str` ("" on failure); the real
                # tool never raises, but the mock or a future version might (Req 9.7).
                resp = await upload_image_to_library_tool(ad_id, payload)
            except Exception as exc:
                logger.error(
                    f"[{task_id}] upload v{index} failed: {type(exc).__name__}: {_redact_text(exc)}"
                )
                continue
            if not (isinstance(resp, str) and resp.strip()):
                logger.error(
                    f"[{task_id}] upload v{index} failed: unusable response "
                    f"({type(resp).__name__}: {_redact_text(resp)!r})"
                )
                continue
            image_id = resp.strip()
            logger.info(f"[{task_id}] upload v{index} → image_id={_redact_text(image_id)}")
            uploaded.append({"id": image_id, "prompt": variation["prompt"]})

        if not uploaded:
            raise VariationUploadFailedError(
                "No se pudo subir ninguna variación a Sinergia",
                details=_edit_error_details(
                    task_id, id_base_image, "upload", f"0/{len(analyzed)} uploads succeeded",
                ),
            )
        # Stored before resolve_urls so a retry never re-uploads (Req 9.10).
        _edit_cp_store(task, task_id, ad_id, "upload", uploaded)

    # ── resolve_urls ────────────────────────────────────────────────────────
    # Registered_Variant = {"id", "url", "prompt"} (Req 10.2). The checkpoint
    # stores URLs after `_strip_signed_urls`; the result of this run returns them
    # unmodified (Req 10.3, 14.8).
    registered: list[dict[str, str]]
    if cp_resolve is not None:
        # 0 uploads, 0 Edit_Sleep, 0 URL_Resolution (Req 14.9).
        _progress(task, task_id, "resolve_urls", "checkpoint")
        registered = cp_resolve
    else:
        _progress(task, task_id, "resolve_urls", f"images={len(uploaded)}")
        # Give the Sinergia library time to index the new images (Req 14.1, 14.10).
        # Module global resolved at call time so tests can patch it (Req 14.2).
        await _edit_sleep(_LIBRARY_INDEX_DELAY_S)
        registered = []
        for item in uploaded:  # sequential on purpose (Req 14.3)
            image_id = item["id"]
            url, attempts, cause = await _resolve_variation_url(
                get_ad_variant_image,
                task_id=task_id, brand_id=brand_id, campaign_id=campaign_id, ad_id=ad_id,
                channel_id=channel_id, variant_id=variant_id, image_name=image_name,
                image_id=image_id,
            )
            if url is None:
                logger.warning(
                    f"[{task_id}] resolve_urls id={_redact_text(image_id)} skipped after "
                    f"{attempts} queries: {_redact_text(cause)}"
                )
                continue
            logger.info(
                f"[{task_id}] resolve_urls id={_redact_text(image_id)} → "
                f"url={_strip_signed_urls(url)} ({attempts} queries)"
            )
            registered.append({"id": image_id, "url": url, "prompt": item["prompt"]})

        if not registered:
            # Retryable; the `upload` checkpoint is kept so a retry never
            # re-uploads, and no `resolve_urls` checkpoint is stored (Req 14.7).
            logger.error(f"[{task_id}] resolve_urls resolved 0/{len(uploaded)} urls")
            raise VariationUrlResolutionError(
                "No se pudo resolver la url de ninguna variación subida",
                details=_edit_error_details(
                    task_id, id_base_image, "resolve_urls", f"0/{len(uploaded)} urls resolved",
                ),
            )
        logger.info(f"[{task_id}] resolve_urls → {len(registered)}/{len(uploaded)} urls resolved")
        _edit_cp_store(task, task_id, ad_id, "resolve_urls", _strip_signed_urls(registered))

    # ── done ────────────────────────────────────────────────────────────────
    _progress(task, task_id, "done", f"variations={len(registered)}")
    return AdVariantImageEditResult(
        task_id=task_id,
        variant_id=variant_id,
        id_base_image=id_base_image,
        status="DONE",
        variations=registered,
    ).model_dump(mode="json")


# ---------------------------------------------------------------------------
# Ad-variant image-edit pipeline — Celery task
# ---------------------------------------------------------------------------

@celery_app.task(
    name="services.job_runner_service.run_edit_ad_variant_image_pipeline",
    bind=True,
    max_retries=3,
)
def run_edit_ad_variant_image_pipeline(
    self,
    brand_id: int,
    campaign_id: int,
    ad_id: int,
    channel_id: int,
    variant_id: int,
    image_name: str,
    id_base_image: str,
    n_variations: int,
    custom_prompt: str | None = None,
    expand_zoom_option: str | None = None,
) -> dict[str, Any]:
    """Celery entry point for the ad-variant image-edit pipeline.

    Retry policy (D7): non-retryable `AdVariantImageEditError` fails immediately;
    other errors retry with 2**n backoff up to `max_retries`, after which the
    original exception is re-raised. No full tracebacks are logged (signed URLs).
    """
    task_id = self.request.id
    logger.info(
        f"[{task_id}] ▶ EditAdVariantImage start — variant={variant_id} "
        f"base_image={id_base_image} n={n_variations} option={expand_zoom_option}"
    )
    self.update_state(state="PROGRESS", meta={
        "step": "starting",
        "variant_id": variant_id,
        "id_base_image": id_base_image,
    })

    try:
        # Fresh event loop per attempt (same reason as run_pipeline_phase1).
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Module global lookup so tests can substitute the coroutine.
            result = loop.run_until_complete(_run_edit_ad_variant_image_pipeline(
                self, task_id,
                brand_id=brand_id,
                campaign_id=campaign_id,
                ad_id=ad_id,
                channel_id=channel_id,
                variant_id=variant_id,
                image_name=image_name,
                id_base_image=id_base_image,
                n_variations=n_variations,
                custom_prompt=custom_prompt,
                expand_zoom_option=expand_zoom_option,
            ))
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception as sg_exc:
                logger.warning(
                    f"[{task_id}] shutdown_asyncgens error (ignored): {_redact_text(sg_exc)}"
                )
            loop.close()
            asyncio.set_event_loop(None)

        logger.info(f"[{task_id}] EditAdVariantImage complete")
        return result
    except Exception as exc:
        from celery.exceptions import MaxRetriesExceededError
        msg = _redact_text(str(exc))
        attempt = self.request.retries + 1
        if not _is_retryable_edit_error(exc):
            logger.error(
                f"[{task_id}] EditAdVariantImage non-retryable failure "
                f"(attempt {attempt}): {type(exc).__name__}: {msg}"
            )
            raise
        if self.request.retries >= self.max_retries:
            logger.error(
                f"[{task_id}] Max retries ({self.max_retries}) exhausted. "
                f"Original: {type(exc).__name__}: {msg}"
            )
            raise exc
        logger.warning(
            f"[{task_id}] EditAdVariantImage failed (attempt {attempt}), "
            f"retrying in {2 ** self.request.retries}s: {type(exc).__name__}: {msg}"
        )
        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:  # defensive, see D7
            logger.error(f"[{task_id}] Max retries exhausted. {type(exc).__name__}: {msg}")
            raise exc


# ---------------------------------------------------------------------------
# Phase 1 — full 7-agent pipeline
# ---------------------------------------------------------------------------

@celery_app.task(name="services.job_runner_service.run_shadow_pipeline", ignore_result=True)
def run_shadow_pipeline(
    id_adset: int,
    n_variants: int = 3,
    project_id: str | None = None,
    id_ad: int | None = None,
    custom_prompt: str | None = None,
):
    """
    Fire-and-forget shadow execution for the Vertex AI Agent Engine.
    This triggers the remote cloud pipeline to run in parallel with our local one.
    """
    logger.info(f"[SHADOW] Triggering Agent Engine for adset={id_adset}")
    try:
        # In a real implementation, you would use the google-genai SDK 
        # to hit the deployed Agent Engine endpoint ID.
        # e.g., client = genai.Client(); client.agents.execute(...)
        logger.info(f"[SHADOW] Agent Engine trigger dispatched successfully.")
    except Exception as e:
        logger.error(f"[SHADOW] Agent Engine trigger failed (ignored): {e}")

@celery_app.task(
    name="services.job_runner_service.run_pipeline_phase1",
    bind=True,
    max_retries=3,
)
def run_pipeline_phase1(
    self,
    id_adset: int,
    n_variants: int = 3,
    project_id: str | None = None,
    id_ad: int | None = None,
    custom_prompt: str | None = None,
    add_variant: bool = True,
    id_variant: list[int] | None = None,
):
    """Run the complete 7-agent pipeline for a variant job."""
    task_id = self.request.id
    logger.info(f"[{task_id}] ▶ Phase1 start — adset={id_adset} n={n_variants}")

    # # --- SHADOW EXECUTION TRIGGER ---
    # try:
    #     # Fire and forget the shadow task so it runs in parallel with the local execution
    #     run_shadow_pipeline.delay(id_adset, n_variants, project_id, id_ad, custom_prompt)
    # except Exception as e:
    #     logger.warning(f"[{task_id}] Failed to dispatch shadow pipeline (ignored): {e}")
    # # --------------------------------

    self.update_state(state="PROGRESS", meta={
        "step": "starting",
        "id_adset": id_adset,
        "n_variants": n_variants,
    })

    try:
        # Create a fresh event loop for each task execution.
        # Celery prefork workers can have a stale/closed loop from a previous
        # task, which makes asyncio.run() raise RuntimeError intermittently.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _run_phase1(self, task_id, id_adset, n_variants, project_id, id_ad, custom_prompt, add_variant, id_variant)
            )
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception as sg_exc:
                logger.warning(f"[{task_id}] shutdown_asyncgens error (ignored): {sg_exc}")
            loop.close()
            asyncio.set_event_loop(None)

        logger.info(f"[{task_id}] Phase1 complete")
        return result
    except Exception as exc:
        from celery.exceptions import MaxRetriesExceededError
        tb = traceback.format_exc()
        logger.error(
            f"[{task_id}] Phase1 failed (attempt {self.request.retries + 1}): "
            f"{type(exc).__name__}: {exc}\n{tb}"
        )
        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:
            logger.error(
                f"[{task_id}] Max retries ({self.max_retries}) exhausted. "
                f"Original: {type(exc).__name__}: {exc}\n{tb}"
            )
            raise


@observe(name="fury.ads_variants_pipeline")
async def _run_phase1(
    task, task_id: str, id_adset: int, n_variants: int, project_id: str | None, id_ad: int | None = None, 
    custom_prompt: str | None = None, add_variant: bool = True, id_variant: list[int] | None = None
) -> dict:
    """Python-driven sequential pipeline — calls each agent directly.

    Agents are created fresh on each job via lazy factories so that
    model/instruction changes in Langfuse take effect without worker restarts.
    """
    from agents.data_collector_agent import make_data_collector_agent
    from agents.estratega_agent import make_estratega_agent
    from agents.copywriter_agent import make_copywriter_agent
    from agents.image_prompter_agent import make_image_prompter_agent
    from agents.validador_agent import make_validador_agent
    from agents.nano_banana_agent import make_nano_banana_agent, generate_images_from_prompts
    from agents.template_mapper_agent import make_template_mapper_agent
    from agents.estratega_adset_agent import make_estratega_adset_agent
    from services.territory_assignment import (
        assign_territories,
        build_estratega_adset_input,
        apply_descriptions,
        territory_to_plan,
    )
    from services.ads_validators import (
        validate_estratega_response,
        validate_estratega_adset_response,
        validate_copywriter_response,
        validate_image_prompter_response,
        validate_validador_response,
    )

    if settings.USE_MOCK_SINERGIA:
        from agents.tools.mock_sinergia import (
            get_adset_context,
            get_a_template_definition,
            get_template_context,
            save_ads,
            get_ctas,
            delete_variants,
        )
    else:
        from agents.tools.campaign_tools import (
            get_adset_context,
            get_a_template_definition,
            get_template_context,
            save_ads,
            get_ctas,
            delete_variants,
        )

    # data_collector_agent  = make_data_collector_agent()
    estratega_agent       = make_estratega_agent(custom_prompt)
    copywriter_agent      = make_copywriter_agent(custom_prompt)
    image_prompter_agent  = make_image_prompter_agent(custom_prompt)
    # validador_agent is created only on the Legacy_Path (after the Diversity_Path
    # branch), so the Diversity_Path never instantiates the legacy Validador (D20).
    # nano_banana_agent     = make_nano_banana_agent()
    # template_mapper_agent = make_template_mapper_agent()

    def _progress(step: str, detail: str = ""):
        if task is not None:
            task.update_state(state="PROGRESS", meta={"step": step, "detail": detail})
        logger.info(f"[{task_id}] → {step} {detail}")

    async def _validate_ctas(copies):
        cta_catalog = await get_ctas()
        if not isinstance(cta_catalog, list):
            cta_catalog = []

        for copy in copies:
            if isinstance(copy, dict):
                final_ctas = []
                ctas = copy.get("cta", []) or []
                for a_cta in ctas:
                    if a_cta in cta_catalog:
                        final_ctas.append(a_cta)
                    else:
                        logger.warning(
                            f"[{task_id}] copywriter CTA '{a_cta}' no está en el catálogo de get_ctas. Se ajusta a ''."
                        )

                # cta_value = copy.get("cta", "")
                # if cta_value and cta_value not in cta_catalog:
                #     logger.warning(
                #         f"[{task_id}] copywriter CTA '{cta_value}' no está en el catálogo de get_ctas. Se ajusta a ''."
                #     )
                #     copy["cta"] = ""

                copy["cta"] = final_ctas

    async def _build_save_ads_payloads(copies: list[dict], *, resolve_template=None) -> list[dict]:
        payloads: list[dict] = []
        for copy in copies:
            if not isinstance(copy, dict):
                continue

            template_id = copy.get("template_id") or copy.get("templateId")
            template_resp = {}
            if template_id:
                try:
                    # Diversity_Path: job cache (P15, D24); Legacy_Path: the tool.
                    template_resp = await (resolve_template or get_a_template_definition)(template_id)
                except Exception as e:
                    logger.error(f"[{task_id}] get_a_template_definition failed for template_id={template_id}: {e}")

            template = {}
            if isinstance(template_resp, dict) and template_resp.get("ok"):
                template = template_resp.get("template") or {}
            elif template_id:
                logger.warning(f"[{task_id}] get_a_template_definition returned invalid response for template_id={template_id}")

            template_elements = template.get("elements") or []
            formats = template.get("formats") or []
            media_template_name = template.get("name") or template.get("template_name") or ""

            element_map: dict[str, dict] = {}
            for element in template_elements:
                element_id = element.get("name") or element.get("id")
                if element_id:
                    element_map[str(element_id)] = element

            media_elements = []
            for element in copy.get("template_elements", []):
                if not isinstance(element, dict):
                    continue
                element_type = element.get("element_type") or element.get("type") or element.get("elementType")
                if element_type not in ("text", "button"):
                    continue

                name = (
                    element.get("element_id")
                    or element.get("name")
                    or element.get("element_name")
                    or element.get("id")
                    or ""
                )
                original = ""
                referenced = element_map.get(str(name)) or element_map.get(str(element.get("element_id"))) or {}
                if referenced:
                    original = ""
                    if isinstance(referenced.get("attributes"), list) and referenced["attributes"]:
                        values = referenced["attributes"][0].get("values", {})
                        original = next(iter(values.values()), "")

                payload_value = element.get("text") or element.get("payload") or element.get("value") or ""
                if not payload_value and element_type == "button":
                    payload_value = copy.get("cta", [])[0] if isinstance(copy.get("cta", []), list) and len(copy.get("cta", [])) > 0 else ""

                # Enforce the overlay element's REAL allowed length, using the SAME
                # formula the funnel-flow validator applies (ADS_08_02): the template
                # placeholder's length + 20% (capped at +10). The template designer
                # sized each text box, so generated text must fit the placeholder's
                # length + margin. `original` is that placeholder text (captured above
                # from the template definition). This is a deterministic guard so
                # overlay text cannot trip the validator. Buttons are never trimmed
                # (their value must match the CTA list exactly). Mutating
                # `element["text"]` in place means the Abyssale render — which reads
                # the same copy object downstream — gets the same fitted text.
                if element_type == "text" and original:
                    orig_len = len(original)
                    real_max = orig_len + min(math.ceil(orig_len * 0.2), 10)
                    if real_max > 0 and len(payload_value) > real_max:
                        fitted = fit_to_limit(payload_value, real_max)
                        if fitted != payload_value:
                            logger.info(
                                f"[{task_id}] MaxChar: trimmed '{name}' "
                                f"{len(payload_value)}->{len(fitted)} "
                                f"(max {real_max} = orig {orig_len} +margin)"
                            )
                        payload_value = fitted
                        element["text"] = fitted

                media_elements.append({
                    "name": name,
                    "type": element_type,
                    "payload": payload_value,
                    "intention": element.get("purpose") or element.get("intention") or "",
                    "original_payload": original,
                })

            media_images_banner = []
            for element in template_elements:
                if element.get("type") != "image":
                    continue
                preview_url = None
                if isinstance(element.get("attributes"), list) and element["attributes"]:
                    values = element["attributes"][0].get("values", {})
                    preview_url = next(iter(values.values()), None)
                media_images_banner.append({
                    "name": element.get("name") or element.get("id") or "",
                    "type": "image",
                    "bucket": None,
                    "image_id": None,
                    "preview_url": preview_url,
                    "thumbnail_id": None,
                    "image_prompts": None,
                    "image_style_id": None,
                    "image_attributes_saved": None,
                    "preferred_image_prompt": None,
                    "image_attributes_generated": None,
                })

            channel_atributes = []
            def add_channel_attribute(name: str, attr_type: str, value: list | None) -> None:
                if not value:
                    return
                # payload = str(value).strip()
                # if not payload:
                #     return
                channel_atributes.append({
                    "name": name,
                    "type": attr_type,
                    "payloads": [{"id": idx, "payload": str(v).strip()} for idx, v in enumerate(value)]
                    # "payloads": [{"id": 0, "payload": payload}],
                })

            add_channel_attribute("headline", "text", copy.get("headline"))
            add_channel_attribute("primary_text", "text", copy.get("primary_text"))
            add_channel_attribute("description", "text", copy.get("description"))
            add_channel_attribute("cta", "button", copy.get("cta"))

            payloads.append({
                "media_template_id": template_id,
                "media_template_name": media_template_name,
                "media_elements": media_elements,
                "media_images_banner": media_images_banner,
                "media_formats": formats,
                "channel_atributes": channel_atributes,
            })

        return payloads

    async def _save_ads_programmatically(
        id_adset: int, ad_id: int, copies: list[dict], *, resolve_template=None
    ) -> list[dict]:
        payloads = await _build_save_ads_payloads(copies, resolve_template=resolve_template)
        if not payloads:
            logger.warning(f"[{task_id}] No save_ads payloads were built for ad={ad_id}")
            return [
                {
                    "plan_id": copy.get("plan_id", ""),
                    "template_id": copy.get("template_id", ""),
                    "saved": False,
                    "ad_id": None,
                    **({"variant_key": copy["variant_key"]} if "variant_key" in copy else {}),
                }
                for copy in copies
                if isinstance(copy, dict)
            ]

        try:
            save_response = await save_ads(id_adset, ad_id, payloads)
        except Exception as e:
            logger.error(f"[{task_id}] save_ads failed for ad={ad_id}: {e}")
            return [
                {
                    "plan_id": copy.get("plan_id", ""),
                    "template_id": copy.get("template_id", ""),
                    "saved": False,
                    "ad_id": None,
                    **({"variant_key": copy["variant_key"]} if "variant_key" in copy else {}),
                }
                for copy in copies
                if isinstance(copy, dict)
            ]

        # Normalize different possible response shapes from save_ads
        # Known shapes:
        # - Real Sinergia: {"ok": True, "ads": {"ok": True, "data": {"ad_set_id":.., "ad_id":.., "created": [{"id":...}, ...]}}}
        # - Simple list: [ {"id":...}, ... ]
        ads = []
        if isinstance(save_response, dict):
            if save_response.get("ok"):
                ads = save_response.get("ads") or []
            else:
                logger.error(f"[{task_id}] save_ads returned ok=false for ad={ad_id}: {save_response}")
        elif isinstance(save_response, list):
            ads = save_response
        else:
            logger.error(f"[{task_id}] save_ads returned unexpected type for ad={ad_id}: {type(save_response).__name__}")

        # Extract created entries when response is nested (Sinergia style)
        created_entries: list[dict] = []
        if isinstance(ads, dict):
            # ads may be {"ok": True, "data": {"created": [...]}} or {"data": {"created": [...]}}
            data = ads.get("data") if isinstance(ads, dict) else None
            if isinstance(data, dict) and isinstance(data.get("created"), list):
                created_entries = data.get("created")
            elif isinstance(ads.get("created"), list):
                created_entries = ads.get("created")
            else:
                # Fallback: single object representing created ad
                created_entries = [ads]
        elif isinstance(ads, list):
            created_entries = ads

        # Map created ids to copies in order. If lengths mismatch, log for debugging.
        if len(created_entries) != len(copies):
            logger.debug(f"[{task_id}] save_ads created_entries length {len(created_entries)} != copies length {len(copies)} for ad={ad_id}. Response={json.dumps(save_response, ensure_ascii=False)}")

        saved_ads = []
        for index, copy in enumerate(copies):
            if not isinstance(copy, dict):
                continue
            returned = created_entries[index] if index < len(created_entries) else {}
            returned_id = None
            if isinstance(returned, dict):
                returned_id = returned.get("id") or returned.get("ad_id") or returned.get("id_ad") or returned.get("variant_id") or None
            entry = {
                "plan_id": copy.get("plan_id", ""),
                "template_id": copy.get("template_id", ""),
                "saved": bool(returned_id),
                "ad_id": returned_id,
            }
            # Diversity_Path copies carry `variant_key` (Req 5.9); legacy copies don't,
            # so the Legacy_Path output stays byte-for-byte identical.
            if "variant_key" in copy:
                entry["variant_key"] = copy["variant_key"]
            saved_ads.append(entry)

        return saved_ads

    # ── STEP 1: Data Collection ─────────────────────────────────────────

    _progress("data_collection", f"adset={id_adset}")
    ads = []
    # Fetch the FULL adset context ONCE and reuse it for every agent below.
    # Previously each agent re-called get_adset_context via its own tool
    # (~6x per run -> ~186k tokens + empty-response failures). We now fetch it
    # here and inject it into each agent's input instead.
    adset_context = await get_adset_context(id_adset)
    # Drop presigned-URL credentials (X-Amz-Credential / -Security-Token /
    # -Signature) before this context is injected into ANY agent prompt — they
    # leak AWS creds to the LLM and trip the credentials safety-guard.
    adset_context = _strip_signed_urls(adset_context)
    logger.info(f"[{task_id}] data_collector done — adset={id_adset}")
    adset_context_json = (
        json.dumps(adset_context, ensure_ascii=False)
        if isinstance(adset_context, (dict, list)) else "{}"
    )

    # ── Diversity_Path (USE_ADSET_CREATIVE_DIVERSITY) ────────────────────
    # Replaces steps 2–10 for every target Ad (Req 2.3). getattr: the flag may be
    # absent from settings (golden test) and the Legacy_Path must not depend on it.
    if getattr(settings, "USE_ADSET_CREATIVE_DIVERSITY", False):
        # Lazy imports (Req 2.4): no agent imports at module level.
        from agents.tools.abyssale_tools import build_abyssale_payload, post_to_abyssale_and_wait
        from agents.validador_adset_agent import make_validador_adset_agent
        from services.adset_diversity import DEFAULT_DECORATIVE_IMAGE_PATTERNS

        # One Template_Definition cache per job (P15, Req 15.1; D24), shared by the
        # Image_Elements lookup and save_ads. The tool name is resolved here, after
        # the lazy import above, so patched module attributes are honoured.
        patterns = list(getattr(settings, "ADSET_DECORATIVE_IMAGE_PATTERNS", DEFAULT_DECORATIVE_IMAGE_PATTERNS))
        fetch_template = get_a_template_definition
        if settings.USE_MOCK_SINERGIA:
            _mock_fetch = get_a_template_definition

            async def fetch_template(template_id: str) -> Any:
                return _as_template_definition_response(await _mock_fetch(template_id))

        template_definitions = _JobTemplateDefinitions(fetch_template, patterns)

        deps = _DiversityDeps(
            get_template_context=get_template_context,
            delete_variants=delete_variants,
            validate_ctas=_validate_ctas,
            save_ads_programmatically=functools.partial(
                _save_ads_programmatically, resolve_template=template_definitions.tool_response
            ),
            template_definitions=template_definitions,
            generate_images=generate_images_from_prompts,
            build_abyssale_payload=build_abyssale_payload,
            post_to_abyssale_and_wait=post_to_abyssale_and_wait,
            make_estratega_adset_agent=make_estratega_adset_agent,
            make_copywriter_agent=make_copywriter_agent,
            make_image_prompter_agent=make_image_prompter_agent,
            make_validador_adset_agent=make_validador_adset_agent,
            progress=_progress,
        )
        return await _run_adset_diversity_path(
            deps, task=task, task_id=task_id, id_adset=id_adset, n_variants=n_variants,
            project_id=project_id, id_ad=id_ad, custom_prompt=custom_prompt,
            add_variant=add_variant, id_variant=id_variant,
            adset_context=adset_context, adset_context_json=adset_context_json,
        )

    # Legacy_Path only (D20): the legacy Validador is never created on the Diversity_Path.
    validador_agent = make_validador_agent()

    if id_ad and id_ad > 0:
        logger.info(f"[{task_id}] ad_id provided, using ad_id={id_ad} directly")
        ads = [{"id": id_ad}]
    else:
        if isinstance(adset_context, dict):
            ads = adset_context.get("adset", {}).get("ads", []) or []
        if not ads:
            ads = []

    all_proposals = []
    all_generated_images = []
    all_saved_ads = []
    all_validation_reports = []
    abyssale_batch_ids = []

    async def _run_pipeline_for_ad(ad_id):
        # ── STEP 2: Strategy ────────────────────────────────────────────────
        _progress("strategy", f"ad={ad_id} n_variants={n_variants}")

        strategy_plans = _load(_cp_key(task_id, ad_id, "strategy"))
        if strategy_plans:
            logger.info(f"[{task_id}] checkpoint hit: strategy ad={ad_id} plans={len(strategy_plans)}")
        else:
            strategy_plans = []
            if settings.USE_TERRITORY_ENGINE:
                # Phase A (Ads Assembly v2): code assigns disjoint territories, then
                # estratega_adset WRITES a concept within each — diversity by construction.
                _progress("phase_a_territories", f"ad={ad_id} n={n_variants}")
                template_ids = []
                if project_id:
                    try:
                        tctx = await get_template_context(project_id)
                        tlist = (tctx or {}).get("templates") or []
                        template_ids = [
                            str(t.get("id") or t.get("template_id"))
                            for t in tlist
                            if isinstance(t, dict) and (t.get("id") or t.get("template_id"))
                        ]
                    except Exception as e:
                        logger.warning(f"[{task_id}] get_template_context failed (territory path): {e}")

                territories = assign_territories(
                    adset_context,
                    n_ads=n_variants,
                    adset_id=id_adset,
                    template_ids=template_ids or None,
                    n_variantes=1,
                )
                if territories:
                    estratega_adset_agent = make_estratega_adset_agent(custom_prompt)
                    adset_input = build_estratega_adset_input(adset_context, territories)
                    try:
                        desc_raw = await _run_agent(
                            estratega_adset_agent,
                            f"adset_{id_adset}_ad_{ad_id}_phaseA",
                            adset_input,
                            validator=validate_estratega_adset_response,
                        )
                    except AgentValidationError as ave:
                        logger.error(f"[{task_id}] estratega_adset failed for ad={ad_id}: {ave}")
                        _progress("phase_a_validation_failed", f"ad={ad_id} errors={ave.errors}")
                        raise ave
                    llm_items = desc_raw if isinstance(desc_raw, list) else ([desc_raw] if desc_raw else [])
                    territories = apply_descriptions(territories, llm_items)
                    strategy_plans = [territory_to_plan(t, i) for i, t in enumerate(territories)]
                    logger.info(f"[{task_id}] territory engine -> {len(strategy_plans)} plans for ad={ad_id}")
                else:
                    logger.warning(f"[{task_id}] territory engine produced no territories for ad={ad_id}; using legacy estratega")

            if not strategy_plans:
                # Legacy path (default): estratega distributes diversity AND writes.
                strat_input = (
                    f"n_variants={n_variants}. id_adset={id_adset} ad_id={ad_id} project_id={project_id}\n"
                    f"Design {n_variants} ad strategy plans.\n"
                    f"FULL ADSET CONTEXT (use this — do NOT call get_adset_context):\n{adset_context_json}\n"
                )

                # Manejar excepciones de validación para que no rompan el pipeline completo
                try:
                    strat_raw = await _run_agent(
                        estratega_agent,
                        f"adset_{id_adset}_ad_{ad_id}_strat",
                        strat_input,
                        validator=validate_estratega_response,
                    )
                except AgentValidationError as ave:
                    logger.error(f"[{task_id}] Estratega validation failed for ad={ad_id}: {ave}")
                    strat_raw = []
                    _progress("strategy_validation_failed", f"ad={ad_id} errors={ave.errors}")
                    raise ave  # re-raise to trigger retry with exponential backoff

                strategy_plans = strat_raw #_parse_json_response(strat_raw)
                if not isinstance(strategy_plans, list):
                    strategy_plans = [strategy_plans] if strategy_plans else []

            _store(_cp_key(task_id, ad_id, "strategy"), strategy_plans, ex=_CHECKPOINT_TTL)
        logger.info(f"[{task_id}] estratega done — ad={ad_id} plans={len(strategy_plans)}")

        # ── STEP 3: Copywriting ─────────────────────────────────────────────
        _progress("copywriting", f"ad={ad_id}")
        copies = _load(_cp_key(task_id, ad_id, "copy"))
        if copies:
            logger.info(f"[{task_id}] checkpoint hit: copy ad={ad_id} copies={len(copies)}")
        else:
            copy_input = (
                f"Generate copy for these {len(strategy_plans)} plans.\n"
                f"Plans: {json.dumps(strategy_plans, ensure_ascii=False)}\n"
                f"id_adset={id_adset} ad_id={ad_id} project_id={project_id}\n"
                f"FULL ADSET CONTEXT (use this — do NOT call get_adset_context):\n{adset_context_json}\n"
            )

            # Manejar excepciones de validación para que no rompan el pipeline completo
            try:
                copy_raw = await _run_agent(
                    copywriter_agent, 
                    f"adset_{id_adset}_ad_{ad_id}_copy", 
                    copy_input,
                    validator=validate_copywriter_response,
                )
            except AgentValidationError as ave:
                logger.error(f"[{task_id}] Copywriter validation failed for ad={ad_id}: {ave}")
                copy_raw = []
                _progress("copywriting_validation_failed", f"ad={ad_id} errors={ave.errors}")
                raise ave  # re-raise to trigger retry with exponential backoff
            
            copies = copy_raw # _parse_json_response(copy_raw)
            if not isinstance(copies, list):
                copies = [copies] if copies else []
            _store(_cp_key(task_id, ad_id, "copy"), copies, ex=_CHECKPOINT_TTL)
        # -------------- Enforce literal CTA from get_ctas catalog --------------
        await _validate_ctas(copies)

        logger.info(f"[{task_id}] copywriter done — ad={ad_id} copies={len(copies)}")

        # ── STEP 4: Image Prompts ────────────────────────────────────────────
        _progress("image_prompts", f"ad={ad_id}")
        image_prompts = _load(_cp_key(task_id, ad_id, "image_prompts"))
        if image_prompts:
            logger.info(f"[{task_id}] checkpoint hit: image_prompts ad={ad_id} prompts={len(image_prompts)}")
        else:
            img_input = (
                f"Generate image prompts for these plans.\n"
                f"Plans: {json.dumps(strategy_plans, ensure_ascii=False)}\n"
                f"Copies: {json.dumps(copies, ensure_ascii=False)}\n"
                f"id_adset={id_adset} ad_id={ad_id}\n"
                f"FULL ADSET CONTEXT (use this — do NOT call get_adset_context):\n{adset_context_json}\n"
            )

            # Manejar excepciones de validación para que no rompan el pipeline completo
            try:
                img_raw = await _run_agent(
                    image_prompter_agent, 
                    f"adset_{id_adset}_ad_{ad_id}_img", 
                    img_input,
                    validator=validate_image_prompter_response,
                )
            except AgentValidationError as ave:
                logger.error(f"[{task_id}] Image Prompter validation failed for ad={ad_id}: {ave}")
                img_raw = []
                _progress("image_prompter_validation_failed", f"ad={ad_id} errors={ave.errors}")
                raise ave  # re-raise to trigger retry with exponential backoff
            
            image_prompts = img_raw # _parse_json_response(img_raw)
            if not isinstance(image_prompts, list):
                image_prompts = [image_prompts] if image_prompts else []
            _store(_cp_key(task_id, ad_id, "image_prompts"), image_prompts, ex=_CHECKPOINT_TTL)
        logger.info(f"[{task_id}] image_prompter done — ad={ad_id} prompts={len(image_prompts)}")

        # ── STEP 5: Validation (with retry) ─────────────────────────────────
        MAX_RETRIES = 3
        iteration = 0
        final_plans = strategy_plans
        final_copies = copies
        final_prompts = image_prompts
        val_result = {}

        if n_variants > 1:
            while iteration < MAX_RETRIES:
                iteration += 1
                _progress("validation", f"ad={ad_id} iteration={iteration}")

                proposals = _build_proposals(final_plans, final_copies, final_prompts, ad_id=ad_id)
                val_input = (
                    f"Validate these {len(proposals)} proposals:\n"
                    f"{json.dumps(proposals, ensure_ascii=False)}"
                )

                # Manejar excepciones de validación para que no rompan el pipeline completo
                try:
                    val_raw = await _run_agent(
                        validador_agent, 
                        f"adset_{id_adset}_ad_{ad_id}_val_{iteration}", 
                        val_input,
                        validator=validate_validador_response,
                    )
                except AgentValidationError as ave:
                    logger.error(f"[{task_id}] Validador execution failed for ad={ad_id} iteration={iteration}: {ave}")
                    val_raw = {}
                    _progress("validation_execution_failed", f"ad={ad_id} iteration={iteration} errors={ave.errors}")
                    if iteration < MAX_RETRIES:
                        logger.info(f"[{task_id}] Retrying validation for ad={ad_id} iteration={iteration + 1} after failure")
                        continue  # retry immediately for the next iteration
                    raise ave  # re-raise to trigger retry with exponential backoff
                
                val_result = val_raw # _parse_json_response(val_raw)
                overall_pass = val_result.get("overall_pass", True) if isinstance(val_result, dict) else True
                logger.info(f"[{task_id}] validador ad={ad_id} iteration={iteration} pass={overall_pass}")

                if overall_pass:
                    break

                if iteration >= MAX_RETRIES:
                    logger.warning(f"[{task_id}] max retries exceeded — ad={ad_id}")
                    break

                failing_ids = set(val_result.get("subset_to_regenerate", []))
                if not failing_ids:
                    break
                _progress("retry_strategy", f"ad={ad_id} regenerating {len(failing_ids)} plans")
                retry_input = (
                    f"Redesign ONLY these plans: {list(failing_ids)}. "
                    f"id_adset={id_adset} ad_id={ad_id}. n_variants={n_variants}. project_id={project_id}\n"
                    f"FULL ADSET CONTEXT (use this — do NOT call get_adset_context):\n{adset_context_json}\n"
                )

                # Manejar excepciones de validación para que no rompan el pipeline completo
                try:
                    retry_raw = await _run_agent(
                        estratega_agent, 
                        f"adset_{id_adset}_ad_{ad_id}_strat_retry_{iteration}", 
                        retry_input,
                        validator=validate_estratega_response,
                    )
                except AgentValidationError as ave:
                    logger.error(f"[{task_id}] Estratega retry validation failed for ad={ad_id} iteration={iteration}: {ave}")
                    retry_raw = []
                    _progress("retry_strategy_validation_failed", f"ad={ad_id} iteration={iteration} errors={ave.errors}")
                    if iteration < MAX_RETRIES:
                        logger.info(f"[{task_id}] Retrying strategy regeneration for ad={ad_id} iteration={iteration + 1} after failure")
                        continue  # retry immediately for the next iteration
                    raise ave  # re-raise to trigger retry with exponential backoff
                
                
                new_plans = retry_raw # _parse_json_response(retry_raw)
                if isinstance(new_plans, list):
                    plan_map = {p["id"]: p for p in final_plans}
                    for p in new_plans:
                        plan_map[p["id"]] = p
                    final_plans = list(plan_map.values())
                _store(_cp_key(task_id, ad_id, "strategy"), final_plans, ex=_CHECKPOINT_TTL)

                # Manejar excepciones de validación para que no rompan el pipeline completo
                try:
                    copy_raw2 = await _run_agent(
                        copywriter_agent, 
                        f"adset_{id_adset}_ad_{ad_id}_copy_retry_{iteration}",
                        f"Copy for: {json.dumps(final_plans, ensure_ascii=False)}\n"
                        f"id_adset={id_adset} ad_id={ad_id}. project_id={project_id}\n"
                        f"FULL ADSET CONTEXT (use this — do NOT call get_adset_context):\n{adset_context_json}\n",
                        validator=validate_copywriter_response,
                    )
                except AgentValidationError as ave:
                    logger.error(f"[{task_id}] Copywriter retry validation failed for ad={ad_id} iteration={iteration}: {ave}")
                    copy_raw2 = []
                    _progress("retry_copywriting_validation_failed", f"ad={ad_id} iteration={iteration} errors={ave.errors}")
                    if iteration < MAX_RETRIES:
                        logger.info(f"[{task_id}] Retrying copywriting regeneration for ad={ad_id} iteration={iteration + 1} after failure")
                        continue  # retry immediately for the next iteration
                    raise ave  # re-raise to trigger retry with exponential backoff

                final_copies = copy_raw2 or final_copies
                _store(_cp_key(task_id, ad_id, "copy"), final_copies, ex=_CHECKPOINT_TTL)

                # Manejar excepciones de validación para que no rompan el pipeline completo
                try:
                    img_raw2 = await _run_agent(
                        image_prompter_agent, 
                        f"adset_{id_adset}_ad_{ad_id}_img_retry_{iteration}",
                        f"Prompts for: {json.dumps(final_plans, ensure_ascii=False)}\n"
                        f"Copies: {json.dumps(final_copies, ensure_ascii=False)}\n"
                        f"id_adset={id_adset} ad_id={ad_id}.\n"
                        f"FULL ADSET CONTEXT (use this — do NOT call get_adset_context):\n{adset_context_json}\n",
                        validator=validate_image_prompter_response
                    )
                except AgentValidationError as ave:
                    logger.error(f"[{task_id}] Image Prompter retry validation failed for ad={ad_id} iteration={iteration}: {ave}")
                    img_raw2 = []
                    _progress("retry_image_prompter_validation_failed", f"ad={ad_id} iteration={iteration} errors={ave.errors}")
                    if iteration < MAX_RETRIES:
                        logger.info(f"[{task_id}] Retrying image prompter regeneration for ad={ad_id} iteration={iteration + 1} after failure")
                        continue  # retry immediately for the next iteration
                    raise ave  # re-raise to trigger retry with exponential backoff

                final_prompts = img_raw2 or final_prompts
                _store(_cp_key(task_id, ad_id, "image_prompts"), final_prompts, ex=_CHECKPOINT_TTL)

        # ── STEP 6: Image Generation ─────────────────────────────────────────
        _progress("image_generation", f"ad={ad_id} prompts={len(final_prompts)}")

        # Hotfix: Por cada item en final_prompts, actulaizar image_prompts[].image_request.technical_specs.aspect_ratio = '9:16'
        for item in final_prompts:
            if item.get('image_prompts'):
                for prompt in item['image_prompts']:
                    prompt['image_request']['technical_specs']['aspect_ratio'] = '9:16'
        # Fin Hotfix

        generated_images = []
        try:
            result = await generate_images_from_prompts(final_prompts, ad_id)
            generated_images = result.get("generated_images", [])
        except Exception as img_exc:
            logger.error(f"[{task_id}] image generation failed ad={ad_id}: {img_exc}")
        logger.info(f"[{task_id}] nano_banana done — ad={ad_id} images={len(generated_images)}")

        if settings.DEBUG and generated_images:
            import base64, os
            out_dir = "/tmp/fury_images"
            os.makedirs(out_dir, exist_ok=True)
            for img in generated_images:
                plan_id = img.get("plan_id", "unknown")
                for a_url in img.get("image_prompts", []):
                    url = a_url.get("image_url", "")
                    if url and url.startswith("data:"):
                        try:
                            _, b64data = url.split(",", 1)
                            img_bytes = base64.b64decode(b64data)
                            path = f"{out_dir}/{task_id[:8]}_{plan_id}_{a_url.get('element_id', 'no-id')}.jpg"
                            with open(path, "wb") as f:
                                f.write(img_bytes)
                            logger.info(f"[DEV] Saved image → {path}")
                        except Exception as e:
                            logger.warning(f"[DEV] Could not save image for plan={plan_id} ad={ad_id}: {e}")

        
        # ── STEP 7: Save Ads to Sinergia  ────────────────────────────────────
        _progress("save_ads", f"ad={ad_id}")
        saved_ads = _load(_cp_key(task_id, ad_id, "saved_ads"))
        if saved_ads:
            logger.info(f"[{task_id}] checkpoint hit: saved_ads ad={ad_id} saved={len(saved_ads)}")
        else:
            saved_ads = await _save_ads_programmatically(id_adset, ad_id, final_copies)
            if saved_ads and saved_ads[0].get("saved"):
                logger.info(f"[{task_id}] save_ads done — ad={ad_id} saved={len(saved_ads)}")
                _store(_cp_key(task_id, ad_id, "saved_ads"), saved_ads, ex=_CHECKPOINT_TTL)
            else:
                logger.warning(f"[{task_id}] save_ads failed — ad={ad_id} saved={len(saved_ads)}")
        
        # ── STEP 8: Template Mapping ─────────────────────────────────────────
        _progress("template_mapping", f"ad={ad_id}")
        from agents.tools.abyssale_tools import build_abyssale_payload, post_to_abyssale_and_wait

        creative_content = _merge_creative(final_plans, final_copies, generated_images, saved_ads, ad_id=ad_id)
        selected_template = (
            (final_plans[0].get("template_id") if final_plans else None)
            or "default"
        )
        payload_result = build_abyssale_payload(creative_content, selected_template, "4:5")
        abyssale_result = await post_to_abyssale_and_wait(task_id, payload_result.get("payload", {}), id_adset, ad_id)
        batch_id = abyssale_result.get("batch_id")
        abyssale_response = abyssale_result.get("abyssale_response", [])
        logger.info(f"[{task_id}] template_mapper done — ad={ad_id} batch_id={batch_id}")

        if batch_id:
            try:
                _redis().set(f"fury:webhook:task:{batch_id}", task_id, ex=86400 * 7)
            except Exception:
                pass

        # ── STEP 9: Assemble final output ────────────────────────────────────
        _progress("waiting_abyssale", f"ad={ad_id}")
        proposals_out = _build_proposals(final_plans, final_copies, final_prompts, ad_id=ad_id)

        if not add_variant and id_variant and isinstance(id_variant, list) and len(id_variant) > 0:
            # ── STEP 10: Delete Old Variants ────────────────────────────────────
            _progress("cleanup_old_variants", f"ad={ad_id}")
            await delete_variants(id_variant)

        return {
            "proposals": proposals_out,
            "validation_report": val_result if isinstance(val_result, dict) else {},
            # "generated_images": generated_images,
            "saved_ads": saved_ads,
            "abyssale_batch_id": batch_id,
        }

    # Limitar concurrencia para evitar sobrecarga y no exceder los rate limits
    # del proveedor de LLM (Gemini ~20 req/min por defecto). Tunable por settings.
    _max_concurrent = int(getattr(settings, "ADS_MAX_CONCURRENT_ADS", 2))
    semaphore = asyncio.Semaphore(_max_concurrent)  # pipelines concurrentes

    async def _run_pipeline_for_ad_with_semaphore(ad_id):
        async with semaphore:
            return await _run_pipeline_for_ad(ad_id)

    # Crear tareas para todos los ads
    tasks = [_run_pipeline_for_ad_with_semaphore(ad.get("id")) for ad in ads]

    # Ejecutar en paralelo
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Procesar resultados
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"[{task_id}] Error in pipeline: {result}")
            #continue  # O manejar el error apropiadamente
            raise result
        all_proposals.extend(result.get("proposals", []))
        # all_generated_images.extend(result.get("generated_images", []))
        all_saved_ads.extend(result.get("saved_ads", []))
        all_validation_reports.append(result.get("validation_report", {}))
        if result.get("abyssale_batch_id"):
            abyssale_batch_ids.append(result.get("abyssale_batch_id"))

    # Agregar delay de espera para asegurar que el webhook de Abyssale tenga tiempo de actualizar la BD antes de que el frontend intente leerlo.
    await asyncio.sleep(15)

    return {
        "variant_job_id": task_id,
        "id_adset": id_adset,
        "status": "WAITING_ABYSSALE",
        "abyssale_batch_ids": abyssale_batch_ids,
        "proposals": all_proposals,
        "validation_reports": all_validation_reports,
        # "generated_images": all_generated_images,
        "saved_ads": all_saved_ads,
    }


# ---------------------------------------------------------------------------
# Diversity_Path (USE_ADSET_CREATIVE_DIVERSITY) — adset-creative-diversity
# ---------------------------------------------------------------------------
# `_run_phase1` runs step 1 (get_adset_context, once) and, with the flag on, hands
# over to `_run_adset_diversity_path`: Ad_Slots → territories assigned once per job
# (checkpoint `adset_territories`) → one Creative_Plan per Ad with n_variants
# Variant_Slots → copy / image prompts / validation loop → images, save_ads,
# Abyssale and delete_variants. Pure helpers live in services/adset_diversity.py
# and services/diversity_checker.py and are imported lazily (Req 2.4).
# `_run_agent`, `_load`, `_store` and `_redis` are resolved as module globals at
# call time so tests can patch them.

_DIVERSITY_MAX_RETRIES = 3          # Req 7.5 — validation-loop iterations per Ad
_ABYSSALE_WEBHOOK_WAIT_S = 15       # same final wait as the Legacy_Path


class _AdDiversityFailure(Exception):
    """Deterministic data failure of a single Ad (Req 4.7, 6.11, 7.6; D4).

    Raised inside the Ad's pipeline and caught by `_run_diversity_ad`: the Ad does not
    call save_ads, Abyssale nor delete_variants, and its Diversity_Report carries
    `ad_failed=True` and `error`. The other Ads continue. The message must be built
    from own data only (ids, project_id, checker messages), never from `str(exc)` of
    external dependencies.
    """

    def __init__(
        self,
        message: str,
        *,
        deterministic_errors: list[str] | None = None,
        deterministic_warnings: list[str] | None = None,
        iterations: int = 0,
        subset_to_regenerate: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.deterministic_errors = list(deterministic_errors or [])
        self.deterministic_warnings = list(deterministic_warnings or [])
        self.iterations = iterations
        self.subset_to_regenerate = list(subset_to_regenerate or [])


@dataclass(frozen=True)
class _TemplateDefinitionFailure:
    """Cached failure of a Template_Definition lookup (P15, Req 15.3; D24).

    `cause` is one of a fixed set built from own data only (Req 15.13):
    ``"get_a_template_definition raised <Class>"``,
    ``"get_a_template_definition returned ok == False"`` or
    ``"empty template definition"``. Never `str(exc)` nor the tool's `error` field.
    """

    template_id: str
    cause: str


_TEMPLATE_DEF_NOT_OK = "get_a_template_definition returned ok == False"
_TEMPLATE_DEF_EMPTY = "empty template definition"


def _as_template_definition_response(raw: Any) -> Any:
    """Adapt the mock Sinergia shape to the real tool's response (D24).

    A dict with ``ok`` passes unchanged; a dict without ``ok`` that is a
    Template_Definition becomes ``{"ok": True, "template": raw}``; any other value
    (including ``{}``) becomes ``{"ok": False}``.
    """
    if isinstance(raw, dict):
        if "ok" in raw:
            return raw
        from services.adset_diversity import is_template_definition  # lazy (D2)

        if is_template_definition(raw):
            return {"ok": True, "template": raw}
    return {"ok": False}


class _JobTemplateDefinitions:
    """Template_Definition cache for one `_run_phase1` execution (P15, Req 15.1; D24).

    Holds one `asyncio.Future` per `template_id`: the first Ad starts the lookup and
    every other Ad with the same Ad_Template awaits the same future, also when Ads
    run concurrently (`ADS_MAX_CONCURRENT_ADS > 1`). `_resolve` never raises
    `Exception`, so the future stores both the success and the failure and `fetch`
    is called at most once per `template_id`. Lives only in memory (never in Redis).
    """

    def __init__(self, fetch: Callable[[str], Awaitable[Any]], patterns: Sequence[str]) -> None:
        self._fetch = fetch
        self._patterns = tuple(patterns)
        self._futures: dict[str, asyncio.Future] = {}
        self._calls: dict[str, int] = {}

    @property
    def calls(self) -> dict[str, int]:
        """Number of `fetch` invocations per `template_id` (diagnostics/tests)."""
        return dict(self._calls)

    async def _get(self, template_id: str) -> "tuple[dict, ImageElements] | _TemplateDefinitionFailure":
        tid = str(template_id)
        future = self._futures.get(tid)
        if future is None:
            # No await between the lookup and the insert: concurrent Ads share it.
            future = asyncio.ensure_future(self._resolve(tid))
            self._futures[tid] = future
        # shield: cancelling one waiting Ad must not cancel the shared lookup.
        return await asyncio.shield(future)

    async def _resolve(self, tid: str) -> "tuple[dict, ImageElements] | _TemplateDefinitionFailure":
        from services.adset_diversity import build_image_elements, is_template_definition  # lazy (D2)

        self._calls[tid] = self._calls.get(tid, 0) + 1
        try:
            raw = await self._fetch(tid)
        except Exception as exc:  # never str(exc) (Req 15.13)
            return _TemplateDefinitionFailure(tid, f"get_a_template_definition raised {type(exc).__name__}")
        if not isinstance(raw, dict) or raw.get("ok") is not True:  # never reads raw["error"]
            return _TemplateDefinitionFailure(tid, _TEMPLATE_DEF_NOT_OK)
        template = raw.get("template")
        if not is_template_definition(template):
            return _TemplateDefinitionFailure(tid, _TEMPLATE_DEF_EMPTY)
        try:
            template = copy.deepcopy(template)
            elements = build_image_elements(tid, template, self._patterns)
        except Exception as exc:  # defensive: keep the "never raises" contract
            return _TemplateDefinitionFailure(tid, f"build_image_elements raised {type(exc).__name__}")
        return template, elements

    async def image_elements(self, template_id: str) -> "ImageElements | _TemplateDefinitionFailure":
        """Image_Elements of the Ad_Template, or the cached failure (Req 15.1, 15.3)."""
        result = await self._get(template_id)
        if isinstance(result, _TemplateDefinitionFailure):
            return result
        return result[1]

    async def tool_response(self, template_id: str) -> dict[str, Any]:
        """For `save_ads`: ``{"ok": True, "template": deepcopy(template)}`` or
        ``{"ok": False}`` (without ``error``), reusing the cache (D24)."""
        result = await self._get(template_id)
        if isinstance(result, _TemplateDefinitionFailure):
            return {"ok": False}
        return {"ok": True, "template": copy.deepcopy(result[0])}


@dataclass(frozen=True)
class _DiversityDeps:
    """Tools, factories and `_run_phase1` closures injected into the Diversity_Path (D1)."""

    get_template_context: Callable[[str], Awaitable[dict[str, Any]]]
    delete_variants: Callable[[list[int]], Awaitable[bool]]
    validate_ctas: Callable[[list[dict]], Awaitable[None]]                    # existing closure
    save_ads_programmatically: Callable[[int, int, list[dict]], Awaitable[list[dict]]]  # existing closure
    generate_images: Callable[..., Awaitable[dict[str, Any]]]                 # generate_images_from_prompts
    build_abyssale_payload: Callable[[list[dict], str, str], dict[str, Any]]
    post_to_abyssale_and_wait: Callable[[str, dict, int, int], Awaitable[dict[str, Any]]]
    make_estratega_adset_agent: Callable[[str | None], Any]
    make_copywriter_agent: Callable[[str | None], Any]
    make_image_prompter_agent: Callable[[str | None], Any]
    make_validador_adset_agent: Callable[[], Any]
    progress: Callable[[str, str], None]
    template_definitions: _JobTemplateDefinitions  # job cache (P15, D24); no default on purpose


@dataclass(frozen=True)
class _DiversityJob:
    """Job-level parameters shared by every Ad of the Diversity_Path."""

    task: Any
    task_id: str
    id_adset: int
    n_variants: int
    project_id: str | None
    id_ad: int | None
    custom_prompt: str | None
    add_variant: bool | None
    id_variant: list[int] | None
    adset_context: dict[str, Any]
    adset_context_json: str


@dataclass(frozen=True)
class _JobTemplates:
    """Templates of the job (P12, D18, D19), shared by every Ad of the Diversity_Path."""

    project_templates: tuple[str, ...]   # Project_Templates, Sinergia order, no duplicates
    template_order: tuple[str, ...]      # permutation seeded with task_id
    failure: str | None = None           # Req 4.7 cause when the resolution failed


@dataclass(frozen=True)
class _DiversityAdInput:
    """One target Ad: its Ad_Slot, Ad_Territory and Forbidden_Territories (Req 3.5, 3.7)."""

    ad_id: int
    ad_slot: int
    territory: "AdDescription"
    all_territories: tuple["AdDescription", ...]
    forbidden: tuple[str, ...]
    templates: _JobTemplates             # P12: the same object for every Ad of the job


@dataclass
class _DiversityAdResult:
    """Output of `_run_diversity_ad`, aggregated into the job result."""

    diversity_report: "DiversityReport"
    proposals: list[dict] = field(default_factory=list)
    validation_report: dict = field(default_factory=dict)
    saved_ads: list[dict] = field(default_factory=list)
    abyssale_batch_id: Any = None   # str or list[str], as returned by post_to_abyssale_and_wait


def _failed_diversity_report(ad_id: int, plan_id: str, failure: _AdDiversityFailure) -> "DiversityReport":
    """Diversity_Report of an Ad that failed deterministically (D4, D5)."""
    return {
        "ad_id": ad_id,
        "plan_id": plan_id,
        "deterministic_pass": not failure.deterministic_errors,
        "deterministic_errors": list(failure.deterministic_errors),
        "deterministic_warnings": list(failure.deterministic_warnings),
        "overall_pass": False,
        "iterations": failure.iterations,
        "subset_to_regenerate": list(failure.subset_to_regenerate),
        "ad_failed": True,
        "error": failure.message,
    }


def _diversity_job_result(task_id: str, id_adset: int, ad_results: list[_DiversityAdResult]) -> dict:
    """Legacy result keys + `diversity_reports` (Req 7.12)."""
    proposals: list[dict] = []
    saved_ads: list[dict] = []
    validation_reports: list[dict] = []
    abyssale_batch_ids: list[str] = []
    diversity_reports: list[dict] = []
    for res in ad_results:
        proposals.extend(res.proposals)
        saved_ads.extend(res.saved_ads)
        validation_reports.append(res.validation_report)
        if res.abyssale_batch_id:
            abyssale_batch_ids.append(res.abyssale_batch_id)
        diversity_reports.append(res.diversity_report)
    return {
        "variant_job_id": task_id,
        "id_adset": id_adset,
        "status": "WAITING_ABYSSALE",
        "abyssale_batch_ids": abyssale_batch_ids,
        "proposals": proposals,
        "validation_reports": validation_reports,
        "saved_ads": saved_ads,
        "diversity_reports": diversity_reports,
    }


async def _run_adset_diversity_path(
    deps: _DiversityDeps,
    *,
    task: Any,
    task_id: str,
    id_adset: int,
    n_variants: int,
    project_id: str | None,
    id_ad: int | None,
    custom_prompt: str | None,
    add_variant: bool | None,
    id_variant: list[int] | None,
    adset_context: dict[str, Any],
    adset_context_json: str,
) -> dict[str, Any]:
    """Steps 2–10 of the Diversity_Path for every target Ad (Req 3–8).

    Returns the legacy result keys plus `diversity_reports` (Req 7.12).
    """
    from services.adset_diversity import extract_adset_ads, resolve_ad_slots

    ctx = adset_context if isinstance(adset_context, dict) else {}
    job = _DiversityJob(
        task=task, task_id=task_id, id_adset=id_adset, n_variants=n_variants,
        project_id=project_id, id_ad=id_ad, custom_prompt=custom_prompt,
        add_variant=add_variant, id_variant=id_variant,
        adset_context=ctx, adset_context_json=adset_context_json,
    )

    # Ad_Slots (Req 3.1, 3.2, 3.5–3.7)
    deps.progress("diversity_ad_slots", f"adset={id_adset}")
    slots = resolve_ad_slots(extract_adset_ads(ctx, task_id), id_ad, task_id)
    if not slots.target_ad_ids:
        # Scenario_1 with no Adset_Ads (Req 3.12): no assign_territories, empty lists.
        logger.warning(f"[{task_id}] adset={id_adset} has no valid ads; nothing to generate")
        return _diversity_job_result(task_id, id_adset, [])
    logger.info(
        f"[{task_id}] diversity slots adset={id_adset} slots={slots.slot_ad_ids} "
        f"targets={slots.target_ad_ids} extra_slot={slots.extra_slot}"
    )

    # Territories, once per job (Req 3.3, 3.11, 3.13)
    deps.progress("diversity_territories", f"adset={id_adset} n_slots={len(slots.slot_ad_ids)}")
    territories = await _load_or_assign_territories(task_id, id_adset, ctx, slots)

    # Templates, once per job, after the territories (P12, D18, D19; Req 4.5, 4.10–4.13).
    # A failure is carried in `templates.failure` and fails each Ad (Req 4.7).
    templates = await _load_or_resolve_templates(deps, job, slots)

    slot_of = {ad_id: index for index, ad_id in enumerate(slots.slot_ad_ids)}
    ad_inputs = []
    for ad_id in slots.target_ad_ids:
        slot = slot_of[ad_id]
        territory = territories[slot]
        ad_inputs.append(_DiversityAdInput(
            ad_id=ad_id,
            ad_slot=slot,
            territory=territory,
            all_territories=tuple(territories),
            forbidden=tuple(territory.territorio_prohibido),
            templates=templates,
        ))

    # Same concurrency bound as the Legacy_Path (ADS_MAX_CONCURRENT_ADS).
    semaphore = asyncio.Semaphore(int(getattr(settings, "ADS_MAX_CONCURRENT_ADS", 2)))

    async def _with_semaphore(ad: _DiversityAdInput) -> _DiversityAdResult:
        async with semaphore:
            return await _run_diversity_ad(deps, ad, job)

    results = await asyncio.gather(*(_with_semaphore(ad) for ad in ad_inputs), return_exceptions=True)
    ad_results: list[_DiversityAdResult] = []
    for result in results:
        if isinstance(result, BaseException):
            # AgentValidationError and job-level errors fail the job → Celery retry.
            logger.error(f"[{task_id}] Error in diversity pipeline: {type(result).__name__}")
            raise result
        ad_results.append(result)

    # Give the Abyssale webhook time to update the DB before the frontend reads it.
    await asyncio.sleep(_ABYSSALE_WEBHOOK_WAIT_S)
    return _diversity_job_result(task_id, id_adset, ad_results)


async def _load_or_assign_territories(
    task_id: str,
    id_adset: int,
    adset_context: dict[str, Any],
    slots: "AdSlotPlan",
) -> list["AdDescription"]:
    """Checkpoint `_cp_key(task_id, id_adset, "adset_territories")` or
    `assign_territories(..., n_variantes=1)` + `bind_territories` (Req 3.3, 3.11, 3.13)."""
    from core.exceptions import AdsetCreativeDiversityError
    from schemas.territory_schemas import AdDescription
    from services.adset_diversity import bind_territories
    from services.territory_assignment import assign_territories

    key = _cp_key(task_id, id_adset, "adset_territories")
    cached = _load(key)
    if cached is not None:
        territories: list[AdDescription] | None = None
        try:
            if isinstance(cached, list):
                territories = [AdDescription.model_validate(t) for t in cached]
        except Exception as exc:
            logger.warning(f"[{task_id}] invalid adset_territories checkpoint: {type(exc).__name__}")
            territories = None
        if territories and [t.ad_id for t in territories] == list(slots.slot_ad_ids):
            logger.info(f"[{task_id}] checkpoint hit: adset_territories adset={id_adset} n={len(territories)}")
            return territories
        logger.warning(
            f"[{task_id}] adset_territories checkpoint does not match the Ad_Slots "
            f"{slots.slot_ad_ids}; recomputing"
        )

    n_ads = len(slots.slot_ad_ids)
    assigned = assign_territories(adset_context, n_ads=n_ads, adset_id=id_adset, n_variantes=1)
    if not assigned:
        raise AdsetCreativeDiversityError(
            f"adset {id_adset} has no product or buyer anchors: "
            f"cannot assign territories to {n_ads} Ad_Slots",
            details={"id_adset": id_adset, "n_ad_slots": n_ads},
        )
    territories = bind_territories(assigned, list(slots.slot_ad_ids))
    _store(key, [t.model_dump(mode="json") for t in territories], ex=_CHECKPOINT_TTL)
    logger.info(f"[{task_id}] territories assigned adset={id_adset} n={len(territories)}")
    return territories


_ADSET_TEMPLATES_STEP = "adset_templates"


def _valid_template_list(value: Any) -> bool:
    """Non-empty list of non-empty strings without duplicates."""
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(t, str) and t for t in value)
        and len(set(value)) == len(value)
    )


def _parse_adset_templates_checkpoint(cached: Any) -> _JobTemplates | None:
    """`_JobTemplates` from a valid `adset_templates` Checkpoint (D18), else None."""
    if not isinstance(cached, dict):
        return None
    project_templates = cached.get("project_templates")
    order = cached.get("template_order")
    if not (_valid_template_list(project_templates) and _valid_template_list(order)):
        return None
    if len(order) != len(project_templates) or set(order) != set(project_templates):
        return None
    return _JobTemplates(project_templates=tuple(project_templates), template_order=tuple(order))


async def _load_or_resolve_templates(
    deps: _DiversityDeps,
    job: _DiversityJob,
    slots: "AdSlotPlan",
) -> _JobTemplates:
    """Checkpoint `_cp_key(task_id, id_adset, "adset_templates")` if valid (no
    get_template_context nor recomputation). Otherwise get_template_context(project_id)
    once → resolve_project_templates → template_order(templates, task_id) → store the
    Checkpoint. An exception, `ok == False` or an empty list return
    `_JobTemplates((), (), failure=<cause>)` without Checkpoint nor raising
    (Req 4.5, 4.7, 4.10–4.13; D18, D19). Logs only template ids, never `str(exc)`."""
    from services.adset_diversity import resolve_project_templates, template_order

    task_id = job.task_id
    key = _cp_key(task_id, job.id_adset, _ADSET_TEMPLATES_STEP)
    cached = _load(key)
    if cached is not None:
        reused = _parse_adset_templates_checkpoint(cached)
        if reused is not None:
            logger.info(
                f"[{task_id}] checkpoint hit: adset_templates adset={job.id_adset} "
                f"n={len(reused.project_templates)} order={list(reused.template_order)}"
            )
            return reused
        logger.warning(f"[{task_id}] invalid adset_templates checkpoint adset={job.id_adset}; resolving again")

    project_id = job.project_id
    try:
        template_context = await deps.get_template_context(project_id)
    except Exception as exc:
        logger.error(
            f"[{task_id}] get_template_context failed adset={job.id_adset}: {type(exc).__name__}"
        )
        return _JobTemplates((), (), failure=f"get_template_context raised {type(exc).__name__}")
    if isinstance(template_context, dict) and template_context.get("ok") is False:
        logger.error(f"[{task_id}] get_template_context returned ok=False adset={job.id_adset}")
        return _JobTemplates((), (), failure="get_template_context returned ok=False")
    project_templates = resolve_project_templates(template_context)
    if not project_templates:
        logger.error(f"[{task_id}] no Project_Templates for project_id={project_id} adset={job.id_adset}")
        return _JobTemplates((), (), failure="get_template_context returned no templates")

    order = template_order(project_templates, task_id)
    _store(key, {"project_templates": list(project_templates), "template_order": list(order)},
           ex=_CHECKPOINT_TTL)
    logger.info(
        f"[{task_id}] adset_templates resolved adset={job.id_adset} "
        f"n={len(project_templates)} order={list(order)} n_slots={len(slots.slot_ad_ids)}"
    )
    return _JobTemplates(project_templates=tuple(project_templates), template_order=tuple(order))


_AD_RESULT_STEP = "ad_result"


def _store_ad_result_checkpoint(job: _DiversityJob, ad_id: int, result: _DiversityAdResult) -> None:
    """Checkpoint of an Ad that went through steps 6–10 (Abyssale submitted). Only stored
    when something was saved, so a failed save_ads is retried on the next attempt."""
    if not any(isinstance(s, dict) and s.get("saved") for s in result.saved_ads or []):
        return
    _store(_cp_key(job.task_id, ad_id, _AD_RESULT_STEP), {
        "diversity_report": result.diversity_report,
        "proposals": result.proposals,
        "validation_report": result.validation_report,
        "saved_ads": result.saved_ads,
        "abyssale_batch_id": result.abyssale_batch_id,
    }, ex=_CHECKPOINT_TTL)


def _load_ad_result_checkpoint(
    job: _DiversityJob, ad_id: int, plan_id: str
) -> _DiversityAdResult | None:
    """`ad_result` Checkpoint of this Ad, or None if absent / not for this plan."""
    cached = _load(_cp_key(job.task_id, ad_id, _AD_RESULT_STEP))
    if not isinstance(cached, dict):
        return None
    report = cached.get("diversity_report")
    if not isinstance(report, dict) or report.get("plan_id") != plan_id or report.get("ad_failed"):
        logger.warning(f"[{job.task_id}] ad_result checkpoint for ad={ad_id} ignored")
        return None
    logger.info(f"[{job.task_id}] checkpoint hit: ad_result ad={ad_id} — skipping steps 2–10")
    return _DiversityAdResult(
        diversity_report=report,
        proposals=list(cached.get("proposals") or []),
        validation_report=dict(cached.get("validation_report") or {}),
        saved_ads=list(cached.get("saved_ads") or []),
        abyssale_batch_id=cached.get("abyssale_batch_id"),
    )


async def _run_diversity_ad(
    deps: _DiversityDeps, ad: _DiversityAdInput, job: _DiversityJob
) -> _DiversityAdResult:
    """Strategy → copy → image prompts → validation loop → images → save_ads →
    Abyssale → delete_variants for one Ad. Catches `_AdDiversityFailure` (D4)."""
    from services.adset_diversity import PLAN_ID_FMT

    plan_id = PLAN_ID_FMT.format(ad_id=ad.ad_id)
    done = _load_ad_result_checkpoint(job, ad.ad_id, plan_id)
    if done is not None:
        # Already finished in a previous attempt of this task_id: no images, save_ads nor
        # Abyssale again (a Celery retry caused by another Ad must not redo this one).
        return done
    try:
        # STEP 2 — Creative_Plan (task 11.2)
        plan, project_templates = await _build_or_load_creative_plan(deps, ad, job)
        # STEP 2b — Image_Elements of the Ad's Ad_Template (P15, Req 15.1, 15.3; D24).
        # A failure here ends the Ad before Copywriter, Image_Prompter, images and save_ads.
        # Propagated to generation, the image_prompts Checkpoint and regenerations (Req
        # 15.4, 15.6, 15.8, 15.9; D26).
        image_elements = await _resolve_ad_image_elements(deps, ad, job, plan)
        # STEPS 3–4 — copywriting and image prompts (Req 5.1–5.8)
        copies, prompts = await _load_or_generate_copies_and_prompts(
            deps, ad, job, plan, image_elements=image_elements,
        )
        # STEP 5 — validation loop (Req 7.1–7.10)
        copies, prompts, report, verdict = await _diversity_validation_loop(
            deps, ad, job, plan, copies, prompts, project_templates=project_templates,
            image_elements=image_elements,
        )
        # STEPS 6–10 — images, save_ads, Abyssale, delete_variants (Req 8, 11.7)
        result = await _finish_diversity_ad(
            deps, ad, job, plan, copies, prompts, report, verdict,
            image_elements=image_elements,
        )
        _store_ad_result_checkpoint(job, ad.ad_id, result)
        return result
    except _AdDiversityFailure as failure:
        logger.error(f"[{job.task_id}] diversity ad failed ad={ad.ad_id}: {failure.message}")
        deps.progress("diversity_ad_failed", f"ad={ad.ad_id}")
        return _DiversityAdResult(diversity_report=_failed_diversity_report(ad.ad_id, plan_id, failure))


async def _resolve_ad_image_elements(
    deps: _DiversityDeps, ad: _DiversityAdInput, job: _DiversityJob, plan: "CreativePlan"
) -> "ImageElements":
    """Image_Elements of the Ad's Ad_Template via the job cache (P15, Req 15.1, 15.3; D24).

    The Ad_Template is the `template_id` of the first Variant_Slot (all slots of an Ad
    share it). A cached `_TemplateDefinitionFailure` makes the Ad fail with
    `_AdDiversityFailure`; the message only carries own data (Req 15.13).
    """
    task_id, ad_id = job.task_id, ad.ad_id
    variants = plan.get("variants") if isinstance(plan, dict) else None
    template_id = variants[0].get("template_id") if variants else None
    if not template_id:
        cause = "creative plan has no template_id"
        logger.error(
            f"[{task_id}] template definition unavailable template_id={template_id} "
            f"ad={ad_id}: {cause}"
        )
        raise _AdDiversityFailure(
            f"template definition unavailable for template_id={template_id} ad_id={ad_id} ({cause})"
        )
    template_id = str(template_id)
    result = await deps.template_definitions.image_elements(template_id)
    if isinstance(result, _TemplateDefinitionFailure):
        logger.error(
            f"[{task_id}] template definition unavailable template_id={template_id} "
            f"ad={ad_id}: {result.cause}"
        )
        raise _AdDiversityFailure(
            f"template definition unavailable for template_id={template_id} "
            f"ad_id={ad_id} ({result.cause})"
        )
    logger.info(
        f"[{task_id}] image elements resolved template_id={template_id} ad={ad_id} "
        f"element_ids={list(result.element_ids)} count={len(result.element_ids)}"
    )
    return result


def _batch_ids(batch_id: Any) -> list[str]:
    """Normalizes `post_to_abyssale_and_wait`'s `batch_id` (str, list or None) to a list
    of non-empty ids (Req 8.7: "", None and [] mean no batch)."""
    if isinstance(batch_id, (list, tuple)):
        return [str(b) for b in batch_id if b]
    return [str(batch_id)] if batch_id else []


def _delete_variants_skip_reason(
    job: _DiversityJob, ad_id: int, saved_ads: list[dict], batch_id: Any
) -> str | None:
    """None if `delete_variants(id_variant)` must run for this Ad (Req 8.3–8.5, 8.7),
    otherwise the reason it is skipped."""
    if job.add_variant is True:
        return "add_variant is True"
    if not isinstance(job.id_variant, list) or not job.id_variant:
        return "id_variant is empty"
    if ad_id != job.id_ad:
        return f"ad_id={ad_id} is not id_ad={job.id_ad}"
    if not any(isinstance(s, dict) and s.get("saved") for s in saved_ads or []):
        return "save_ads saved no variant"
    if not _batch_ids(batch_id):
        return "Abyssale returned no batch_id"
    return None


async def _finish_diversity_ad(
    deps: _DiversityDeps,
    ad: _DiversityAdInput,
    job: _DiversityJob,
    plan: "CreativePlan",
    copies: list[dict],
    prompts: list[dict],
    report: "DiversityReport",
    verdict: dict,
    *,
    image_elements: "ImageElements | None" = None,
) -> _DiversityAdResult:
    """Steps 6–10 of one Ad, mirroring the Legacy_Path with matching by `variant_key`:
    images (Req 11.7) → save_ads once, payloads in Variant_Slot order (Req 8.1) →
    merge_variant_creative + Abyssale (Req 5.9, 8.2, 8.7) → delete_variants
    (Req 8.3–8.5, 8.7).

    With `image_elements`, the prompts sent to the Image_Generator are filtered to the
    Ad_Template's Image_Elements (P15, Req 15.10, 15.13; D27); proposals and
    Checkpoints keep using the unfiltered `final_prompts`."""
    from services.adset_diversity import (
        build_variant_proposals,
        filter_image_prompts,
        merge_by_variant_key,
        merge_variant_creative,
    )

    task_id, id_adset, ad_id = job.task_id, job.id_adset, ad.ad_id
    slots = list(plan.get("variants", []))
    # One item per Variant_Slot, in slot order (Req 8.1).
    final_copies = merge_by_variant_key(copies, [], slots)
    final_prompts = merge_by_variant_key(prompts, [], slots)

    # Prompts for the Image_Generator (D27): unchanged without Image_Elements.
    generator_prompts = final_prompts
    if image_elements is not None:
        filtered, dropped = filter_image_prompts(final_prompts, image_elements.element_ids)
        for variant_key, element_id in dropped:
            logger.warning(
                f"[{task_id}] image prompt dropped ad={ad_id} "
                f"variant_key={variant_key} element_id={element_id}"
            )
        # Variants left without elements are not sent to the generator (Req 15.13).
        generator_prompts = [item for item in filtered if item.get("image_prompts")]

    # ── STEP 6: Image Generation (Req 11.7) ──────────────────────────────
    # Hotfix: Por cada item en generator_prompts, actulaizar image_prompts[].image_request.technical_specs.aspect_ratio = '9:16'
    for item in generator_prompts:
        if item.get('image_prompts'):
            for prompt in item['image_prompts']:
                prompt['image_request']['technical_specs']['aspect_ratio'] = '9:16'
    # Fin Hotfix

    deps.progress("image_generation", f"ad={ad_id} prompts={len(generator_prompts)}")
    generated_images: list[dict] = []
    if image_elements is not None and not generator_prompts:
        # Nothing to generate (Req 15.13): the Image_Generator is not invoked.
        generated_images = []
    else:
        try:
            result = await deps.generate_images(generator_prompts, ad_id)
            images = result.get("generated_images", []) if isinstance(result, dict) else []
            generated_images = images if isinstance(images, list) else []
        except Exception as img_exc:
            logger.error(f"[{task_id}] image generation failed ad={ad_id}: {type(img_exc).__name__}")
            generated_images = []
    logger.info(f"[{task_id}] nano_banana done — ad={ad_id} images={len(generated_images)}")

    # ── STEP 7: save_ads, once per Ad (Req 8.1) ──────────────────────────
    deps.progress("save_ads", f"ad={ad_id}")
    saved_key = _cp_key(task_id, ad_id, "saved_ads")
    saved_ads = _load(saved_key)
    if isinstance(saved_ads, list) and saved_ads:
        logger.info(f"[{task_id}] checkpoint hit: saved_ads ad={ad_id} saved={len(saved_ads)}")
    else:
        saved_ads = await deps.save_ads_programmatically(id_adset, ad_id, final_copies)
        saved_ads = saved_ads if isinstance(saved_ads, list) else []
        if any(isinstance(s, dict) and s.get("saved") for s in saved_ads):
            logger.info(f"[{task_id}] save_ads done — ad={ad_id} saved={len(saved_ads)}")
            _store(saved_key, saved_ads, ex=_CHECKPOINT_TTL)
        else:
            logger.warning(f"[{task_id}] save_ads failed — ad={ad_id} saved={len(saved_ads)}")

    # ── STEP 8: Abyssale (Req 8.2, 8.7) ──────────────────────────────────
    deps.progress("template_mapping", f"ad={ad_id}")
    creative_content = merge_variant_creative(plan, final_copies, generated_images, saved_ads, ad_id)
    selected_template = (slots[0].get("template_id") if slots else None) or "default"
    batch_id: Any = None
    try:
        payload_result = deps.build_abyssale_payload(creative_content, selected_template, "4:5")
        payload = payload_result.get("payload", {}) if isinstance(payload_result, dict) else {}
        abyssale_result = await deps.post_to_abyssale_and_wait(task_id, payload, id_adset, ad_id)
        batch_id = abyssale_result.get("batch_id") if isinstance(abyssale_result, dict) else None
    except Exception as aby_exc:
        logger.warning(f"[{task_id}] Abyssale submission failed ad={ad_id}: {type(aby_exc).__name__}")
        batch_id = None
    logger.info(f"[{task_id}] template_mapper done — ad={ad_id} batch_id={batch_id}")

    # Webhook registration, as in the Legacy_Path (non-fatal).
    for bid in _batch_ids(batch_id):
        try:
            _redis().set(f"fury:webhook:task:{bid}", task_id, ex=86400 * 7)
        except Exception:
            pass

    # ── STEP 9: Assemble output ──────────────────────────────────────────
    deps.progress("waiting_abyssale", f"ad={ad_id}")
    proposals_out = build_variant_proposals(plan, final_copies, final_prompts, ad_id)

    # ── STEP 10: delete_variants, after Abyssale (Req 8.3–8.5, 8.7) ──────
    skip_reason = _delete_variants_skip_reason(job, ad_id, saved_ads, batch_id)
    if skip_reason is None:
        deps.progress("cleanup_old_variants", f"ad={ad_id}")
        await deps.delete_variants(job.id_variant)
    elif job.add_variant is True:
        logger.info(f"[{task_id}] delete_variants skipped ad={ad_id}: {skip_reason}")
    else:
        logger.warning(f"[{task_id}] delete_variants skipped ad={ad_id}: {skip_reason}")

    return _DiversityAdResult(
        diversity_report=report,
        proposals=proposals_out,
        validation_report=verdict if isinstance(verdict, dict) else {},
        saved_ads=saved_ads,
        abyssale_batch_id=batch_id or None,
    )


async def _build_or_load_creative_plan(
    deps: _DiversityDeps, ad: _DiversityAdInput, job: _DiversityJob
) -> tuple["CreativePlan", list[str]]:
    """Checkpoint `strategy` (D10) or estratega_adset + Variant_Slots +
    check_territories/check_variant_slots/check_ad_templates (Req 4, 6.10–6.12, D16).

    Templates come from `ad.templates` (P12, D18, D19), resolved once per job by
    `_load_or_resolve_templates`; this function never calls get_template_context.
    If `ad.templates.failure` is set (and there is no reusable `strategy` checkpoint)
    the Ad fails with `_AdDiversityFailure` before invoking the Estratega_Adset (Req 4.7).
    Variant_Slots and the Ad_Template map use `ad.templates.template_order`; the
    checks receive `ad.templates.project_templates` (Req 4.5, 4.6, 6.6, 6.12).
    The `strategy` checkpoint is reused only if every Variant_Slot's template_id equals
    ad_template_for_slot(ad.ad_slot, ad.templates.template_order); otherwise (or with an
    empty Template_Order) it is ignored and the plan is recomputed (Req 4.8, 4.12).
    A reused checkpoint goes through ensure_variant_angles (Req 14.5, D22) and is stored
    again if its angles were recomputed; a new plan adds check_variant_angles to the
    checks before the Copywriter (Req 6.11, 6.13).
    Returns (plan, project_templates); from checkpoint, project_templates =
    plan["_project_templates"] (D14)."""
    from services.adset_diversity import (
        PLAN_ID_FMT,
        ad_template_for_slot,
        build_creative_plan,
        build_estratega_message,
        build_variant_slots,
        ensure_variant_angles,
        slot_ad_templates,
    )
    from services.ads_validators import validate_estratega_adset_response
    from services.diversity_checker import (
        check_ad_templates,
        check_territories,
        check_variant_angles,
        check_variant_slots,
    )
    from services.territory_assignment import apply_descriptions, inventory_anchors, unwrap_adset

    task_id, ad_id = job.task_id, ad.ad_id
    plan_id = PLAN_ID_FMT.format(ad_id=ad_id)
    key = _cp_key(task_id, ad_id, "strategy")

    # Checkpoint `strategy` (Req 4.8, D10, D14): reuse without estratega nor templates.
    cached = _load(key)
    if cached is not None:
        cached_templates = cached.get("_project_templates") if isinstance(cached, dict) else None
        if (
            isinstance(cached, dict)
            and cached.get("id") == plan_id
            and isinstance(cached.get("variants"), list)
            and isinstance(cached_templates, list)
            and cached_templates
        ):
            # Coherence with the job's Template_Order (Req 4.8, 4.12; P12, D18): every
            # Variant_Slot must carry ad_template_for_slot(ad_slot, template_order). With an
            # empty Template_Order (failed resolution) the checkpoint is incoherent and
            # ad_template_for_slot is never called.
            job_order = list(ad.templates.template_order)
            expected = ad_template_for_slot(ad.ad_slot, job_order) if job_order else None
            mismatch = None
            for slot in cached["variants"]:
                got = slot.get("template_id") if isinstance(slot, dict) else None
                if expected is None or got != expected:
                    mismatch = got
                    break
            if expected is not None and mismatch is None:
                logger.info(f"[{task_id}] checkpoint hit: strategy ad={ad_id} plan={plan_id}")
                # Variant_Angles (Req 14.5; P14, D22): recompute them if any slot lacks a
                # valid angle, without Estratega_Adset, Sinergia nor Template_Order, and
                # store the corrected plan. The 6.11 checks are not repeated.
                cached, recomputed = ensure_variant_angles(cached)  # type: ignore[arg-type]
                if recomputed:
                    logger.warning(
                        f"[{task_id}] strategy checkpoint for ad={ad_id} without valid "
                        f"Variant_Angles; recomputed"
                    )
                    _store(key, cached, ex=_CHECKPOINT_TTL)
                return cached, [str(t) for t in cached_templates]  # type: ignore[return-value]
            logger.warning(
                f"[{task_id}] strategy checkpoint for ad={ad_id} incoherent with Template_Order: "
                f"checkpoint template_id={mismatch!r} expected template_id={expected!r}; recomputing"
            )
        else:
            logger.warning(
                f"[{task_id}] strategy checkpoint for ad={ad_id} is not a Creative_Plan "
                f"{plan_id!r}; recomputing"
            )

    # Job templates (Req 4.5, 4.7; P12, D18, D19): fail before the Estratega_Adset.
    project_id = job.project_id
    if ad.templates.failure:
        raise _AdDiversityFailure(
            f"no templates for project_id={project_id} ad_id={ad_id} ({ad.templates.failure})"
        )
    order = list(ad.templates.template_order)
    project_templates = list(ad.templates.project_templates)

    # Estratega_Adset writes the concept within the assigned territory (Req 4.2, 4.4).
    deps.progress("diversity_strategy", f"ad={ad_id} slot={ad.ad_slot}")
    territory = ad.territory.model_copy(deep=True)  # never mutate the shared territories
    agent = deps.make_estratega_adset_agent(job.custom_prompt)  # Req 8.6
    message = build_estratega_message(job.adset_context, job.adset_context_json, territory)
    try:
        raw = await _run_agent(
            agent,
            f"adset_{job.id_adset}_ad_{ad_id}_div_strat",
            message,
            validator=validate_estratega_adset_response,
        )
    except AgentValidationError as ave:
        logger.error(f"[{task_id}] estratega_adset failed for ad={ad_id}: {ave.errors}")
        deps.progress("diversity_strategy_validation_failed", f"ad={ad_id}")
        raise
    llm_items = raw if isinstance(raw, list) else ([raw] if raw else [])
    territory = apply_descriptions([territory], llm_items)[0]
    if not (territory.concept or "").strip():
        logger.error(f"[{task_id}] estratega_adset returned no concept for ad={ad_id}")
        raise AgentValidationError(
            f"estratega_adset returned no concept for ad={ad_id}",
            errors=["concept missing"],
            step="estratega_adset",
            code="ERR_MISSING_CONCEPT",
        )

    # Creative_Plan with n_variants Variant_Slots over the Template_Order
    # (Req 4.1, 4.3, 4.5, 4.6, 4.9; P12).
    slots = build_variant_slots(plan_id, ad.ad_slot, job.n_variants, order)
    plan = build_creative_plan(territory, ad_id, ad.ad_slot, slots)
    plan["_project_templates"] = list(project_templates)  # D14

    # Deterministic checks before the Copywriter (Req 6.2, 6.3, 6.6, 6.7, 6.11).
    adset = unwrap_adset(job.adset_context)
    territory_check = check_territories(
        list(ad.all_territories),
        product_pool_size=len(inventory_anchors(adset, "product")),
        buyer_pool_size=len(inventory_anchors(adset, "buyer")),
    )
    slot_check = check_variant_slots(plan, project_templates, job.n_variants)
    # Req 6.13 / 6.10 (P14, D22): Variant_Angles of the slots (set by build_variant_slots).
    angle_check = check_variant_angles(plan, job.n_variants)
    # Req 6.12 / 6.10 (D16): Ad_Templates between Ad_Slots, from the pure slot map.
    ad_template_check = check_ad_templates(
        slot_ad_templates(len(ad.all_territories), order), project_templates
    )
    errors = [i.message for i in territory_check.errors if ad.ad_slot in i.ad_slots]
    errors += slot_check.error_messages()
    errors += angle_check.error_messages()
    errors += [i.message for i in ad_template_check.errors if ad.ad_slot in i.ad_slots]
    warnings = [i.message for i in territory_check.warnings if ad.ad_slot in i.ad_slots]
    warnings += slot_check.warning_messages()
    warnings += angle_check.warning_messages()
    warnings += [i.message for i in ad_template_check.warnings if ad.ad_slot in i.ad_slots]
    for warning in warnings:
        logger.warning(f"[{task_id}] diversity warning ad={ad_id}: {warning}")
    if errors:
        raise _AdDiversityFailure(
            f"deterministic diversity errors for ad_id={ad_id}: " + "; ".join(errors),
            deterministic_errors=errors,
            deterministic_warnings=warnings,
        )

    _store(key, plan, ex=_CHECKPOINT_TTL)
    logger.info(
        f"[{task_id}] creative plan ad={ad_id} plan={plan_id} "
        f"templates={[s['template_id'] for s in slots]}"
    )
    return plan, list(project_templates)


# Initial Copywriter / Image_Prompter calls: total attempts per Ad. In production the
# models returned empty answers (tokens_out=0) or dropped `variant_key`; one more call
# with the rejection reasons is far cheaper than failing the whole Celery job.
_DIVERSITY_AGENT_ATTEMPTS = 2
_RETRYABLE_AGENT_CODES = frozenset({
    "ERR_EMPTY_RESPONSE", "ERR_VARIANT_SHAPE", "ERR_INVALID_JSON", "ERR_INVALID_STRUCTURE",
})
# Any per-field shape error of the Copywriter / Image_Prompter base validators.
_RETRYABLE_AGENT_CODE_PREFIXES = ("ERR_COPY_", "ERR_PROMPT_")


def _is_retryable_agent_code(code: Any) -> bool:
    return isinstance(code, str) and (
        code in _RETRYABLE_AGENT_CODES or code.startswith(_RETRYABLE_AGENT_CODE_PREFIXES)
    )


async def _run_variant_agent(
    agent: Any,
    user_id: str,
    message: str,
    validator: Callable[[str], Any],
    *,
    attempts: int,
    task_id: str,
    label: str,
    ad_id: int,
) -> Any:
    """`_run_agent` with up to `attempts` calls. Only empty responses and Variant_Slot
    shape errors are retried; the retry message appends the rejection reasons (our own
    validator messages, never external data). Any other error, or the last failure, is
    re-raised unchanged."""
    attempts = max(1, attempts)
    current = message
    for attempt in range(1, attempts + 1):
        try:
            return await _run_agent(agent, user_id, current, validator=validator)
        except AgentValidationError as ave:
            if attempt >= attempts or not _is_retryable_agent_code(getattr(ave, "code", None)):
                raise
            logger.warning(
                f"[{task_id}] {label} response rejected for ad={ad_id} "
                f"(attempt {attempt}/{attempts}, {ave.code}); retrying"
            )
            reasons = "\n".join(f"- {e}" for e in (ave.errors or [])[:20])
            current = (
                f"{message}\n"
                f"YOUR PREVIOUS ANSWER WAS REJECTED:\n{reasons}\n"
                f"Answer again with ONLY the JSON array, following the OUTPUT IDENTITY "
                f"rules above exactly.\n"
            )
    raise AssertionError("unreachable")  # pragma: no cover


async def _generate_variant_copies(
    deps: _DiversityDeps,
    ad: _DiversityAdInput,
    job: _DiversityJob,
    plan: "CreativePlan",
    slots: list["VariantSlot"],
    *,
    user_id: str,
    attempts: int = 1,
) -> list[dict]:
    """One Copywriter invocation for `slots` (all Variant_Slots or a subset when
    regenerating) with the composite validator `kind="copy"` (Req 5.1–5.3, 8.6).

    Raises `AgentValidationError` if the response fails `validate_copywriter_response`
    or the per-Variant_Slot shape; never stores a Checkpoint (the caller does, only with
    valid responses). Reused by `_regenerate_variants` (task 11.4)."""
    from services.adset_diversity import build_copy_message, make_variant_validator
    from services.ads_validators import validate_copywriter_response

    plan_id = plan.get("id", "")
    agent = deps.make_copywriter_agent(job.custom_prompt)  # Req 8.6
    message = build_copy_message(
        plan, slots, list(ad.forbidden), job.adset_context_json,
        id_adset=job.id_adset, ad_id=ad.ad_id, project_id=job.project_id or "",
    )
    validator = make_variant_validator(validate_copywriter_response, slots, plan_id, kind="copy")
    try:
        raw = await _run_variant_agent(
            agent, user_id, message, validator, attempts=attempts,
            task_id=job.task_id, label="copywriter", ad_id=ad.ad_id,
        )
    except AgentValidationError as ave:
        logger.error(f"[{job.task_id}] copywriter validation failed for ad={ad.ad_id}: {ave.errors}")
        deps.progress("diversity_copywriting_validation_failed", f"ad={ad.ad_id}")
        raise
    return raw if isinstance(raw, list) else ([raw] if raw else [])


async def _generate_variant_prompts(
    deps: _DiversityDeps,
    ad: _DiversityAdInput,
    job: _DiversityJob,
    plan: "CreativePlan",
    slots: list["VariantSlot"],
    copies: list[dict],
    *,
    user_id: str,
    attempts: int = 1,
    image_elements: "ImageElements | None" = None,
) -> list[dict]:
    """One Image_Prompter invocation for `slots` with the composite validator
    `kind="image_prompt"` (Req 5.7, 5.8, 8.6). Raises `AgentValidationError` on an
    invalid response; never stores a Checkpoint. Reused by `_regenerate_variants`.

    With `image_elements` the message carries the IMAGE ELEMENTS block and the
    validator also applies the Image_Elements_Checker (P15, Req 15.4, 15.6, 15.8)."""
    from services.adset_diversity import build_image_prompt_message, make_variant_validator
    from services.ads_validators import validate_image_prompter_response

    plan_id = plan.get("id", "")
    agent = deps.make_image_prompter_agent(job.custom_prompt)  # Req 8.6
    message = build_image_prompt_message(
        plan, slots, copies, job.adset_context_json,
        id_adset=job.id_adset, ad_id=ad.ad_id, image_elements=image_elements,
    )
    validator = make_variant_validator(
        validate_image_prompter_response, slots, plan_id, kind="image_prompt",
        image_elements=None if image_elements is None else image_elements.element_ids,
    )
    try:
        raw = await _run_variant_agent(
            agent, user_id, message, validator, attempts=attempts,
            task_id=job.task_id, label="image_prompter", ad_id=ad.ad_id,
        )
    except AgentValidationError as ave:
        logger.error(f"[{job.task_id}] image_prompter validation failed for ad={ad.ad_id}: {ave.errors}")
        deps.progress("diversity_image_prompter_validation_failed", f"ad={ad.ad_id}")
        raise
    return raw if isinstance(raw, list) else ([raw] if raw else [])


def _load_variant_checkpoint(
    job: _DiversityJob, ad_id: int, step: str, plan: "CreativePlan", *, kind: str,
    image_elements: "ImageElements | None" = None,
) -> list[dict] | None:
    """Checkpoint `copy` / `image_prompts` of the Diversity_Path, or None.

    Checkpoints are only stored with valid responses, so a shape mismatch means the
    Checkpoint was written by another path (flag changed between retries of the same
    task_id, as in D10): it is ignored with a warning and regenerated. With
    `kind="image_prompt"` and `image_elements`, a Checkpoint that fails the
    Image_Elements_Checker is also ignored and regenerated (P15, Req 15.9; D26)."""
    from services.adset_diversity import check_image_elements, check_variant_items

    cached = _load(_cp_key(job.task_id, ad_id, step))
    if not cached:
        return None
    shape_errors = check_variant_items(cached, plan.get("variants", []), plan.get("id", ""), kind=kind)
    if shape_errors:
        logger.warning(
            f"[{job.task_id}] {step} checkpoint for ad={ad_id} does not match the "
            f"Variant_Slots of {plan.get('id')!r}; regenerating"
        )
        return None
    if kind == "image_prompt" and image_elements is not None:
        element_errors = check_image_elements(cached, image_elements)
        if element_errors:
            logger.warning(
                f"[{job.task_id}] image_prompts checkpoint for ad={ad_id} fails the "
                f"Image_Elements check ({len(element_errors)} error(s)); regenerating"
            )
            return None
    logger.info(f"[{job.task_id}] checkpoint hit: {step} ad={ad_id} n={len(cached)}")
    return cached


async def _load_or_generate_copies_and_prompts(
    deps: _DiversityDeps, ad: _DiversityAdInput, job: _DiversityJob, plan: "CreativePlan",
    *, image_elements: "ImageElements | None" = None,
) -> tuple[list[dict], list[dict]]:
    """Initial copywriting and image prompts of one Ad (Req 5.1–5.8).

    Checkpoint `copy` or one Copywriter call; `_validate_ctas` always (also from the
    Checkpoint, Req 5.4); Checkpoint `image_prompts` or one Image_Prompter call.
    Checkpoints are stored only after the composite validator accepted the response."""
    ad_id = ad.ad_id
    slots = list(plan.get("variants", []))

    # STEP 3 — Copywriting (Req 5.1–5.6)
    deps.progress("diversity_copywriting", f"ad={ad_id} n_variants={len(slots)}")
    copies = _load_variant_checkpoint(job, ad_id, "copy", plan, kind="copy")
    if copies is None:
        copies = await _generate_variant_copies(
            deps, ad, job, plan, slots, user_id=f"adset_{job.id_adset}_ad_{ad_id}_div_copy",
            attempts=_DIVERSITY_AGENT_ATTEMPTS,
        )
        _store(_cp_key(job.task_id, ad_id, "copy"), copies, ex=_CHECKPOINT_TTL)
    # Literal CTAs from the get_ctas catalog, whatever the copies' origin (Req 5.4).
    await deps.validate_ctas(copies)
    logger.info(f"[{job.task_id}] diversity copywriter done — ad={ad_id} copies={len(copies)}")

    # STEP 4 — Image prompts (Req 5.7, 5.8)
    deps.progress("diversity_image_prompts", f"ad={ad_id}")
    prompts = _load_variant_checkpoint(
        job, ad_id, "image_prompts", plan, kind="image_prompt", image_elements=image_elements,
    )
    if prompts is None:
        prompts = await _generate_variant_prompts(
            deps, ad, job, plan, slots, copies, user_id=f"adset_{job.id_adset}_ad_{ad_id}_div_img",
            attempts=_DIVERSITY_AGENT_ATTEMPTS, image_elements=image_elements,
        )
        _store(_cp_key(job.task_id, ad_id, "image_prompts"), prompts, ex=_CHECKPOINT_TTL)
    logger.info(f"[{job.task_id}] diversity image_prompter done — ad={ad_id} prompts={len(prompts)}")
    return copies, prompts


async def _diversity_validation_loop(
    deps: _DiversityDeps,
    ad: _DiversityAdInput,
    job: _DiversityJob,
    plan: "CreativePlan",
    copies: list[dict],
    prompts: list[dict],
    *,
    project_templates: list[str],
    image_elements: "ImageElements | None" = None,
) -> tuple[list[dict], list[dict], "DiversityReport", dict]:
    """Req 7.1–7.10, 7.13; `_DIVERSITY_MAX_RETRIES` iterations (D20). Returns (copies,
    prompts, diversity_report, last Validador_Adset verdict or `{}` if never invoked).

    Each iteration runs the Diversity_Checker first (Req 7.1):
    - checker errors → the Validador_Adset is NOT invoked (Req 7.2): on a non-final
      iteration only the checker's failing variant_keys are regenerated (Req 7.4, D7);
      on the last one the loop ends and the Ad fails with `_AdDiversityFailure` (Req 7.6).
    - checker clean → Validador_Adset (created lazily, once per Ad, never custom_prompt;
      Req 8.6, 13.2) with the reduced message and the checker's warnings (D21). Only
      `overall_pass` and `subset_to_regenerate` are used (Req 13.4):
      `overall_pass` → approved; empty filtered subset (D8) or last iteration →
      warning, report `overall_pass=False`, continue (Req 7.7); otherwise regenerate
      only the filtered subset (D20) and run the next iteration.
    `AgentValidationError` of the Validador_Adset: next iteration without regenerating
    (Req 7.8) or re-raised on the last one (Req 7.9)."""
    from services.adset_diversity import build_validador_message, build_variant_proposals
    from services.ads_validators import validate_validador_response
    from services.diversity_checker import check_variants

    task_id, ad_id = job.task_id, ad.ad_id
    plan_id = plan.get("id", "")
    slot_keys = [s["variant_key"] for s in plan.get("variants", [])]
    slot_key_set = set(slot_keys)
    validador_agent = None  # created on first need (D20)

    verdict: dict = {}
    subset: list[str] = []
    validador_pass = False
    check = None
    iteration = 0
    while iteration < _DIVERSITY_MAX_RETRIES:
        iteration += 1
        last = iteration == _DIVERSITY_MAX_RETRIES
        deps.progress("diversity_validation", f"ad={ad_id} iteration={iteration}")

        # Req 7.1 — deterministic checks first.
        check = check_variants(
            plan, copies, prompts,
            project_templates=project_templates,
            n_variants=len(slot_keys),
            forbidden=list(ad.forbidden),
        )
        if not check.ok:
            # Req 7.2 — no Validador_Adset call while the checker reports errors.
            det_keys = check.failing_variant_keys() & slot_key_set
            logger.warning(
                f"[{task_id}] diversity checker ad={ad_id} iteration={iteration} "
                f"errors={check.error_messages()} keys={sorted(det_keys)}"
            )
            if last:
                break  # Req 7.6 — failure below
            if det_keys:
                # Req 7.4, D7, D9 — regenerate only the checker's failing variants.
                deps.progress(
                    "diversity_regenerate", f"ad={ad_id} iteration={iteration} n={len(det_keys)}"
                )
                copies, prompts = await _regenerate_variants(
                    deps, ad, job, plan, det_keys, copies, prompts, iteration=iteration,
                    image_elements=image_elements,
                )
            continue

        if validador_agent is None:
            validador_agent = deps.make_validador_adset_agent()  # never custom_prompt (Req 8.6)
        proposals = build_variant_proposals(plan, copies, prompts, ad_id)  # Req 7.14 unchanged
        message = build_validador_message(
            plan, proposals, list(ad.forbidden), job.adset_context_json,
            check.warning_messages(),
        )
        try:
            raw = await _run_agent(
                validador_agent,
                f"adset_{job.id_adset}_ad_{ad_id}_div_val_{iteration}",
                message,
                validator=validate_validador_response,
            )
        except AgentValidationError as ave:
            logger.error(
                f"[{task_id}] validador_adset failed for ad={ad_id} iteration={iteration}: "
                f"{ave.errors}"
            )
            deps.progress("diversity_validation_execution_failed", f"ad={ad_id} iteration={iteration}")
            if last:
                raise  # Req 7.9 — Phase1_Task retries with its backoff
            continue  # Req 7.8 — next iteration without regenerating

        # Req 13.4 — only `overall_pass` and `subset_to_regenerate` are used.
        verdict = raw if isinstance(raw, dict) else {}
        validador_pass = verdict.get("overall_pass") is True
        raw_subset = verdict.get("subset_to_regenerate")
        raw_subset = raw_subset if isinstance(raw_subset, list) else []
        # D8, Req 7.13 — keep only this Ad's variant_keys (slot order, no duplicates).
        subset = [k for k in slot_keys if k in raw_subset]
        unknown = [k for k in raw_subset if k not in slot_key_set]
        if unknown:
            logger.warning(
                f"[{task_id}] validador_adset ad={ad_id} iteration={iteration} returned "
                f"unknown variant_keys in subset_to_regenerate: {unknown!r}; ignored"
            )
        logger.info(
            f"[{task_id}] validador_adset ad={ad_id} iteration={iteration} "
            f"pass={validador_pass} subset={subset}"
        )

        if validador_pass:
            break
        if not subset or last:
            # Req 7.7 — the semantic verdict never aborts the Ad.
            logger.warning(
                f"[{task_id}] validador_adset did not approve ad={ad_id} after "
                f"iteration={iteration} (subset={subset}); continuing with overall_pass=False"
            )
            break

        # Req 7.4, D20 — regenerate only the filtered subset.
        deps.progress("diversity_regenerate", f"ad={ad_id} iteration={iteration} n={len(subset)}")
        copies, prompts = await _regenerate_variants(
            deps, ad, job, plan, set(subset), copies, prompts, iteration=iteration,
            image_elements=image_elements,
        )

    deterministic_pass = check is not None and check.ok
    det_errors = check.error_messages() if check is not None else []
    det_warnings = check.warning_messages() if check is not None else []
    if not deterministic_pass:
        # Req 7.6 — persistent deterministic errors: Ad fails without images.
        raise _AdDiversityFailure(
            f"deterministic diversity errors for ad_id={ad_id} after {iteration} "
            f"iteration(s): " + "; ".join(det_errors),
            deterministic_errors=det_errors,
            deterministic_warnings=det_warnings,
            iterations=iteration,
            subset_to_regenerate=subset,
        )

    report: "DiversityReport" = {
        "ad_id": ad_id,
        "plan_id": plan_id,
        "deterministic_pass": True,
        "deterministic_errors": [],
        "deterministic_warnings": det_warnings,
        "overall_pass": validador_pass,
        "iterations": iteration,
        "subset_to_regenerate": subset,
        "ad_failed": False,
        "error": None,
    }
    return copies, prompts, report, verdict


async def _regenerate_variants(
    deps: _DiversityDeps,
    ad: _DiversityAdInput,
    job: _DiversityJob,
    plan: "CreativePlan",
    keys: set[str],
    copies: list[dict],
    prompts: list[dict],
    *,
    iteration: int,
    image_elements: "ImageElements | None" = None,
) -> tuple[list[dict], list[dict]]:
    """Copywriter then Image_Prompter only for `keys`; merge_by_variant_key;
    _validate_ctas on the new copies; _store(copy) and _store(image_prompts)
    (Req 7.4, 7.5). On AgentValidationError keeps the previous ones (Req 7.10).

    The Creative_Plan and the Variant_Slots (`template_id`) are never modified; the
    Copywriter and the Image_Prompter receive only the Variant_Slots in `keys` and their
    composite validators require exactly one item per slot (D9). Checkpoints are stored
    only when both regenerations succeed, so they always match the returned state."""
    from services.adset_diversity import merge_by_variant_key

    ad_id = ad.ad_id
    slots = list(plan.get("variants", []))
    subset_slots = [s for s in slots if s["variant_key"] in keys]
    if not subset_slots:
        return copies, prompts
    try:
        new_copies = await _generate_variant_copies(
            deps, ad, job, plan, subset_slots,
            user_id=f"adset_{job.id_adset}_ad_{ad_id}_div_copy_retry_{iteration}",
        )
        await deps.validate_ctas(new_copies)  # Req 5.4 on the regenerated copies
        merged_copies = merge_by_variant_key(copies, new_copies, slots)
        new_prompts = await _generate_variant_prompts(
            deps, ad, job, plan, subset_slots, merged_copies,
            user_id=f"adset_{job.id_adset}_ad_{ad_id}_div_img_retry_{iteration}",
            image_elements=image_elements,  # Req 15.8 — a mismatch ends in Req 7.10
        )
    except AgentValidationError:
        if iteration >= _DIVERSITY_MAX_RETRIES:
            raise  # defensive: regenerations only happen on non-final iterations (D9)
        logger.warning(
            f"[{job.task_id}] regeneration failed for ad={ad_id} iteration={iteration}; "
            f"keeping previous copies and image prompts"
        )
        return copies, prompts
    merged_prompts = merge_by_variant_key(prompts, new_prompts, slots)

    # Req 7.5 — Checkpoints reflect the state after each successful regeneration.
    _store(_cp_key(job.task_id, ad_id, "copy"), merged_copies, ex=_CHECKPOINT_TTL)
    _store(_cp_key(job.task_id, ad_id, "image_prompts"), merged_prompts, ex=_CHECKPOINT_TTL)
    logger.info(
        f"[{job.task_id}] regenerated ad={ad_id} iteration={iteration} "
        f"keys={[s['variant_key'] for s in subset_slots]}"
    )
    return merged_copies, merged_prompts


def _build_proposals(plans: list, copies: list, prompts: list, ad_id=None) -> list:
    """Merge plans + copies + image_prompts into a proposals list."""
    copy_map = {c.get("plan_id", c.get("id", "")): c for c in copies}
    prompt_map = {p.get("plan_id", ""): p.get("image_prompts", []) for p in prompts}
    result = []
    for plan in plans:
        pid = plan.get("id", "")
        copy = copy_map.get(pid, {})
        result.append({
            "ad_id": ad_id,
            "plan_id": pid,
            "plan": plan,
            "copy": copy,
            "image_prompts": prompt_map.get(pid, ""),
        })
    return result


def _merge_creative(plans: list, copies: list, images: list, saved_ads: list, ad_id=None) -> list:
    """Merge plans + copies + generated images for Abyssale payload."""
    copy_map = {c.get("plan_id", c.get("id", "")): c for c in copies}
    img_map = {i.get("plan_id", i.get("id", "")): i for i in images}
    ad_channels = {s.get("plan_id", s.get("id", "")): s for s in saved_ads}

    result = []
    for plan in plans:
        pid = plan.get("id", "")
        result.append({
            "ad_id": ad_id,
            "plan": plan,
            "copy": copy_map.get(pid, {}),
            "image": img_map.get(pid),
            "ad_channel": ad_channels.get(pid, {}),
        })
    return result



# ---------------------------------------------------------------------------
# Trigger AI Expansion
# ---------------------------------------------------------------------------

@celery_app.task(name="services.job_runner_service.trigger_ai_expansion")
def trigger_ai_expansion(task_id: str, renders: list[dict]):
    import httpx
    logger.info(f"[{task_id}] → trigger_ai_expansion renders={len(renders)}")
    _store(f"fury:result:{task_id}:renders_4_5", renders)

    try:
        response = httpx.post(
            f"{settings.AI_EXPANSION_URL}/expand",
            json={
                "task_id": task_id,
                "renders": renders,
                "callback_url": settings.AI_EXPANSION_WEBHOOK_URL,
            },
            timeout=30,
        )
        response.raise_for_status()
        expansion_batch_id = response.json().get("batch_id")
        if expansion_batch_id:
            _redis().set(
                f"fury:webhook:task:{expansion_batch_id}", task_id, ex=86400 * 7
            )
        logger.info(f"[{task_id}] AI Expansion dispatched batch={expansion_batch_id}")
    except Exception as e:
        logger.error(f"[{task_id}] AI Expansion failed: {e}")


# ---------------------------------------------------------------------------
# Finalize job
# ---------------------------------------------------------------------------

@celery_app.task(name="services.job_runner_service.finalize_job")
def finalize_job(task_id: str, expanded_renders: list[dict]):
    logger.info(f"[{task_id}] → finalize_job")
    renders_4_5 = _load(f"fury:result:{task_id}:renders_4_5") or []
    proposals = _load(f"fury:result:{task_id}:proposals") or {}

    result = {
        "variant_job_id": task_id,
        "status": "DONE",
        "proposals": proposals,
        "renders": {"4:5": renders_4_5, "expanded": expanded_renders},
    }
    celery_app.backend.store_result(task_id, result, "SUCCESS")
    logger.info(f"[{task_id}] ✅ DONE")


# ---------------------------------------------------------------------------
# Mark job failed
# ---------------------------------------------------------------------------

@celery_app.task(name="services.job_runner_service.mark_job_failed")
def mark_job_failed(task_id: str, reason: str):
    celery_app.backend.store_result(task_id, {"error": reason}, "FAILURE")
    logger.warning(f"[{task_id}] ❌ FAILED: {reason}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_response(text):
    """Parse JSON from an agent response — handles arrays [...] and objects {...}.

    Accepts an ALREADY-PARSED dict/list and returns it untouched — see the twin
    helper in persona_job_runner_service: `run_agent` returns the parsed
    `ValidationResult.data` when a validator supplies it, so parsing must be
    idempotent rather than assuming a string.
    """
    import re
    if isinstance(text, (dict, list)):
        return text
    if not text or not text.strip():
        return {}
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    cleaned = cleaned.strip()
    # Try direct parse first (agent returned clean JSON)

    try:
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Failed to parse JSON directly: {e} — trying to extract from text...")
        pass
    # Try to extract array first, then object
    for pattern in (r"\[.*\]", r"\{.*\}"):
        match = re.search(pattern, cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception as e:
                logger.error(f"Failed to parse JSON from pattern {pattern}: {e}")
                pass
    return {"raw": text}
