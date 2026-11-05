"""NanoBanana Agent — generates real images from prompts using the image API."""
import asyncio
import base64
import re
from collections.abc import Awaitable, Callable
from typing import Any
from google.adk.agents import Agent
from core.config import settings
from core.adk_config import get_agent_config_from_langfuse
from core.logging import get_logger
from agents.guards import safety_guard_before_model, safety_guard_after_model
if settings.USE_MOCK_SINERGIA:
    from agents.tools.mock_sinergia import (upload_image_to_library as upload_image_to_library_tool)
else:
    from agents.tools.campaign_tools import (upload_image_to_library as upload_image_to_library_tool)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Image generation tool — plug your API here
# ---------------------------------------------------------------------------

def _get_mime_type_from_url(url: str) -> str:
    ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
    }.get(ext, "image/jpeg")


def _safe_url(url: Any) -> str:
    """URL sin query string para logs (Req 11.8, D13): never log Signed_URL parameters."""
    return str(url or "").partition("?")[0]


# HL-2630: cap concurrent image generations to bound peak memory (see
# IMAGE_GEN_MAX_CONCURRENCY). One semaphore per running event loop — all ads of a job
# share that loop, so this caps the whole job; keyed by loop and pruned so each new
# job/loop gets a fresh one (asyncio primitives bind to the loop that created them).
_img_semaphores: dict = {}


def _image_semaphore() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    sem = _img_semaphores.get(loop)
    if sem is None:
        _img_semaphores.clear()
        sem = asyncio.Semaphore(max(1, getattr(settings, "IMAGE_GEN_MAX_CONCURRENCY", 2)))
        _img_semaphores[loop] = sem
    return sem


async def generate_images_from_prompts(
    image_prompts: list[dict],
    ad_id: int | str,
    upload_image_to_library: bool = True,
) -> dict[str, Any]:
    """Generate real images from image_prompter output using the configured image API.

    Each prompt is generated concurrently via asyncio.gather().

    Args:
        image_prompts: List of { plan_id, image_prompts, visual_style, aspect_ratio }
                       from the ImagePrompter agent.

    Returns:
        Dict with generated_images list: { plan_id, image_url, image_prompt }
    """
    async def _generate_single(prompt_data: dict) -> dict:
        plan_id = prompt_data.get("plan_id", "")
        # prompts = prompt_data.get("image_prompts", [])
        # aspect_ratio = prompt_data.get("aspect_ratio", "4:5")

        try:
            import base64
            from google import genai as gai
            from google.genai import types as genai_types

            # HL-2630: give the Gemini call a real client-side timeout. HttpOptions.timeout is
            # in MILLISECONDS. Without it a stalled request hangs the worker until it's
            # OOM/SIGKILLed (observed 15-18 min) instead of erroring so Celery can retry.
            _gen_timeout_s = max(10, getattr(settings, "IMAGE_GEN_TIMEOUT_SECONDS", 120))
            client = gai.Client(http_options=genai_types.HttpOptions(
                api_version="v1alpha",
                timeout=_gen_timeout_s * 1000,
            ))

            for item in prompt_data.get("image_prompts", []):

                # Try Imagen 3 first (requires Vertex AI / ADC)
                # try:
                #     result = await asyncio.to_thread(
                #         client.models.generate_images,
                #         model= "gemini-2.5-flash",
                #         prompt=item.get('image_prompt', ''),
                #         config=genai_types.GenerateImagesConfig(
                #             number_of_images=1,
                #             aspect_ratio=item.get('aspect_ratio', '4:5'),
                #         ),
                #     )
                #     if result.generated_images:
                #         image_bytes = result.generated_images[0].image.image_bytes
                #         b64 = base64.b64encode(image_bytes).decode()
                #         image_url = f"data:image/png;base64,{b64}"
                #         logger.info(f"NanoBanana [Imagen3] plan={plan_id}: OK ({len(image_bytes)} bytes)")
                #         item["image_url"] = image_url
                #         continue
                #         # return {"plan_id": plan_id, "image_url": image_url, "image_prompt": item.get('image_prompt', '')}
                # except Exception as imagen_err:
                #     logger.warning(f"NanoBanana Imagen3 unavailable for plan={plan_id}: {imagen_err} — trying Gemini Flash")

                try:
                    # Fallback: Gemini 2.0 Flash with native image output (works with AI Studio key)
                    image_url = None
                    mime_type = 'image/png'
                    contents = []

                    # Preparate content with base image if available
                    base_image_url = prompt_data.get('base_image_url')
                    if base_image_url:
                        import httpx
                        try:
                            img_bytes = (await asyncio.to_thread(httpx.get, base_image_url, follow_redirects=True, timeout=30)) #.content
                            
                            if img_bytes.status_code == 200 and img_bytes.content:
                                contents.append(genai_types.Part.from_bytes(data=img_bytes.content, mime_type=_get_mime_type_from_url(base_image_url)))
                            else:
                                # Req 11.1/11.8: skip the base image; log URL without query
                                logger.warning(
                                    f"NanoBanana: empty image bytes from {_safe_url(base_image_url)} "
                                    f"(status={getattr(img_bytes, 'status_code', None)}) plan={plan_id}"
                                )
                        except Exception as dl_err:
                            logger.warning(
                                f"NanoBanana: failed to download {_safe_url(base_image_url)} "
                                f"plan={plan_id}: {type(dl_err).__name__}"
                            )
                    
                    # Prepare content with reference images (base64 strings) if available
                    reference_images = prompt_data.get('reference_images', [])
                    if reference_images:
                        for ref_img in reference_images:
                            try:
                                # Convert base64 string to binary
                                if ref_img and ref_img.startswith('data:image/'):
                                    # Extract mime type and b64 data
                                    header, b64data = ref_img.split(',', 1)
                                    import base64
                                    img_bytes = base64.b64decode(b64data)
                                    
                                    # Determine mime type from header
                                    mime_type_ref = header.split(':')[1].split(';')[0] if ':' in header else 'image/png'
                                    contents.append(genai_types.Part.from_bytes(data=img_bytes, mime_type=mime_type_ref))
                                    logger.info(f"NanoBanana: Added reference image (base64) for plan={plan_id}")
                                else:
                                    logger.warning(f"NanoBanana: invalid reference image format for plan={plan_id}")
                            except Exception as ref_err:
                                logger.warning(f"NanoBanana: failed to process reference image for plan={plan_id}: {type(ref_err).__name__}")
                    
                    # Prepare content with product image if available
                    product_image_urls = prompt_data.get('product_image_urls', []) # item.get('image_request', {}).get("technical_specs", {}).get("product_image_sources", [])

                    # HL-2630: the image_prompter is an LLM — the product URLs it writes into
                    # product_image_urls are presigned S3 links (~1500 chars of ?X-Amz-Signature=...)
                    # that the model cannot reproduce verbatim, so it drops the query string. The
                    # resulting UNSIGNED url 403s on the private bucket in the download below, so
                    # Gemini gets no product photo and invents the product (intermittent, since
                    # the LLM sometimes keeps the full url). Fix: re-fetch FRESH, fully-signed urls in
                    # code from the short product_id (which the LLM can reproduce), bypassing the LLM
                    # transcription entirely. Falls back to the prompt-provided urls on any failure.
                    _product_id = prompt_data.get('product_id')
                    if _product_id:
                        try:
                            from agents.tools.campaign_tools import get_image_from_library
                            _fresh_urls = await get_image_from_library(str(_product_id))
                            if _fresh_urls:
                                product_image_urls = _fresh_urls
                                logger.info(
                                    f"NanoBanana: re-fetched {len(_fresh_urls)} signed product url(s) "
                                    f"for product_id={_product_id} plan={plan_id}"
                                )
                            else:
                                logger.warning(
                                    f"NanoBanana: fresh product url re-fetch returned empty for "
                                    f"product_id={_product_id} plan={plan_id}; using prompt-provided urls"
                                )
                        except Exception as _refetch_err:
                            logger.warning(
                                f"NanoBanana: fresh product url re-fetch failed for "
                                f"product_id={_product_id} plan={plan_id}: {type(_refetch_err).__name__}; "
                                f"using prompt-provided urls"
                            )

                    if product_image_urls:
                        import httpx
                        image_parts = []
                        for url in product_image_urls:
                            try:
                                img_bytes = (await asyncio.to_thread(httpx.get, url, follow_redirects=True, timeout=30))
                                if img_bytes.status_code == 200 and img_bytes.content:
                                    image_parts.append(genai_types.Part.from_bytes(data=img_bytes.content, mime_type=_get_mime_type_from_url(url)))
                                else:
                                    # Req 11.2/11.8: skip this product image; log URL without query
                                    logger.warning(
                                        f"NanoBanana: empty image bytes from {_safe_url(url)} "
                                        f"(status={getattr(img_bytes, 'status_code', None)}) plan={plan_id}"
                                    )
                            except Exception as dl_err:
                                logger.warning(
                                    f"NanoBanana: failed to download {_safe_url(url)} "
                                    f"plan={plan_id}: {type(dl_err).__name__}"
                                )

                        contents.extend(image_parts)
                        contents.append(
                            genai_types.Part.from_text(
                                text=f"Use these product images and composite them into the following scene: {item.get('image_prompt', '')}\n - JSON prompt: {item.get('image_request')}"
                            )
                        )
                        logger.info(f"NanoBanana: Using {len(image_parts)} product images for plan={plan_id}")
                    else:
                        # Text-only prompt
                        contents.append(genai_types.Part.from_text(text=item.get('image_prompt', ''))) # item.get('image_prompt', '')
                    
                    aspect_ratio = item.get('image_request', {}).get("technical_specs", {}).get('aspect_ratio', '9:16')
                    logger.info(f"NanoBanana: Sending generation request to Gemini Flash for plan={plan_id} with aspect_ratio={aspect_ratio}")
                    # HL-2630: asyncio.wait_for + the client HTTP timeout only bound this call if
                    # the underlying blocking request actually returns — wait_for CANNOT cancel a
                    # call already running inside asyncio.to_thread (observed: a 27-min hang where
                    # neither fired, because the SDK's AFC loop never returned). AFC is now disabled
                    # below so the call makes a single request; the hard guarantee against any
                    # remaining hang is the Celery task_soft_time_limit (see celery_app.py).
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            client.models.generate_content,
                            model=NANO_BANANA2_MODEL,
                            contents=contents,
                            config=genai_types.GenerateContentConfig(
                                response_modalities=["IMAGE"],
                                image_config=genai_types.ImageConfig(
                                    aspect_ratio=aspect_ratio,
                                ),
                                # HL-2630: disable Automatic Function Calling. The SDK turns AFC
                                # on by default (logs: "AFC is enabled with max remote calls: 10")
                                # and even warns against its direct use in generate_content. For
                                # pure image generation we never want tool-calling; with AFC on, a
                                # prompt that doesn't return an image on the first turn — e.g. the
                                # composite "scene-only, do NOT draw the product" prompt — can make
                                # the SDK loop up to 10 remote calls, which showed up as a 27-min
                                # hang with no image and no error. Force one request/response.
                                automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(
                                    disable=True
                                ),
                            ),
                        ),
                        timeout=_gen_timeout_s + 15,
                    )
                    
                    for part in (response.candidates[0].content.parts if response.candidates else []):
                        if hasattr(part, "inline_data") and part.inline_data:
                            b64 = base64.b64encode(part.inline_data.data).decode()
                            mime = part.inline_data.mime_type or "image/png"
                            image_url = f"data:{mime};base64,{b64}"
                            mime_type = mime
                            break

                    item["image_url"] = image_url
                    item["image_mime_type"] = mime_type
                    if image_url:
                        logger.info(f"NanoBanana [GeminiFlash] plan={plan_id}: OK")
                    else:
                        # Req 11.4: no candidates / no inline_data
                        logger.warning(f"NanoBanana [GeminiFlash] plan={plan_id}: no image in response")
                        item["image_error"] = "NoImageInResponse"
                except Exception as e:
                    # Req 11.3/11.8: includes TimeoutError from wait_for; class name only
                    logger.error(
                        f"NanoBanana Gemini Flash generation failed for plan={plan_id}: {type(e).__name__}"
                    )
                    item["image_url"] = None
                    item["image_mime_type"] = 'image/png'
                    item["image_error"] = type(e).__name__

        except Exception as exc:
            # Req 11.3: client creation (or any outer) failure marks every item of this prompt
            logger.error(f"NanoBanana image generation failed for plan={plan_id}: {type(exc).__name__}")
            for item in prompt_data.get("image_prompts", None) or []:
                if isinstance(item, dict) and not item.get("image_url") and not item.get("image_error"):
                    item["image_url"] = None
                    item["image_error"] = type(exc).__name__

        # return {"plan_id": plan_id, "image_url": image_url, "image_prompt": prompt}
        return prompt_data

    # Prompts generated concurrently, but bounded by a semaphore so peak memory stays
    # within the worker (unbounded fan-out OOM-killed it — HL-2630).
    _sem = _image_semaphore()

    async def _bounded(p: dict) -> dict:
        async with _sem:
            return await _generate_single(p)

    results = await asyncio.gather(
        *[_bounded(p) for p in image_prompts],
        return_exceptions=True,
    )

    generated = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Req 11.8: class name only (str(result) may carry signed URLs / keys)
            logger.error(f"Image generation failed for prompt {i}: {type(result).__name__}")
            failed = {
                "plan_id": image_prompts[i].get("plan_id", ""),
                "image_url": None,
                "error": type(result).__name__,
            }
            if "variant_key" in image_prompts[i]:
                failed["variant_key"] = image_prompts[i].get("variant_key")
            generated.append(failed)
        else:
            generated.append(result)

    if upload_image_to_library:
        for g in generated:    
            # Req 9.1/9.2: include the prompt that produced the image ("" if missing / not a str)
            images_data = [{'image_data': item.get("image_url"), 'image_name': item.get("element_id"), 
                            'mime_type': item.get("image_mime_type"), 'plan_id': g.get("plan_id"),
                            'image_prompt': item["image_prompt"] if isinstance(item.get("image_prompt"), str) else ""} 
                        for item in g.get('image_prompts', []) if item.get("image_url")]
            logger.info(f"NanoBanana generation completed: {len(images_data)}/{len(image_prompts)} images generated successfully")

            for image in images_data:
                # Req 9.7: log only keys, plan_id, image_name and lengths (never base64 nor prompt text)
                # (loguru: f-string, '%s' placeholders are not interpolated)
                logger.info(
                    f"NanoBanana uploading image to library: keys={sorted(image.keys())} "
                    f"plan_id={image.get('plan_id', '')} image_name={image.get('image_name')} "
                    f"image_data_len={len(image.get('image_data') or '')} "
                    f"image_prompt_len={len(image.get('image_prompt') or '')}"
                )
                # Upload image with upload_image_to_library tool and add image_id with the returned ID from the library
                try:
                    upload_result = await upload_image_to_library_tool(ad_id, image)
                    if upload_result:
                        image_id = upload_result
                        image["image_id"] = image_id
                        logger.info(f"NanoBanana uploaded image for plan {image.get('plan_id', '')} to library with ID {image_id}")
                        # Actualizar la lista 'generated' con el ID de la imagen subida a la biblioteca, si el upload fue exitoso
                        for item in g.get('image_prompts', []):
                            if item.get("element_id") == image.get("image_name"):
                                item["image_id"] = image.get("image_id")
                                break

                    else:
                        logger.error(f"NanoBanana failed to upload image for plan {image.get('plan_id', '')} to library")
                except Exception as upload_exc:
                    # Req 11.6/11.8: no image_id; class name only
                    image.pop("image_id", None)
                    logger.error(
                        f"NanoBanana failed to upload image for plan {image.get('plan_id', '')} to library: "
                        f"{type(upload_exc).__name__}"
                    )

    return {"ok": True, "generated_images": generated}


# ---------------------------------------------------------------------------
# Image_Editor — edit an existing ad-variant image (ad-variant image-edit pipeline)
# ---------------------------------------------------------------------------
# Used by services/job_runner_service._run_edit_ad_variant_image_pipeline, step
# `image_editing`. Sends the ORIGINAL base-image bytes plus the deterministic
# Edit_Instruction to NanoBanana2 and returns N edited variations. Additive only:
# generate_images_from_prompts / make_nano_banana_agent are untouched (Req 7.2).

NANO_BANANA2_MODEL = "gemini-3.1-flash-image-preview"  # same model as generate_images_from_prompts
NANO_BANANA2_1_MODEL = "gemini-nano-banana-2.1"
_EDIT_RATE_LIMIT_BACKOFF_S: tuple[int, ...] = (1, 2, 4)  # Req 7.4: up to 3 retries
_EDIT_MIN_VARIATIONS = 1
_EDIT_MAX_VARIATIONS = 10


def _is_image_rate_limit_error(exc: BaseException) -> bool:
    """429 / RESOURCE_EXHAUSTED: google.genai APIError with code 429, or any error whose
    message carries the markers used by helpers.agent._is_rate_limit_error."""
    try:
        from google.genai import errors as genai_errors
        if isinstance(exc, genai_errors.APIError) and getattr(exc, "code", None) == 429:
            return True
    except Exception:  # SDK import problems must not break classification
        pass
    from helpers.agent import _is_rate_limit_error
    return _is_rate_limit_error(exc)  # type: ignore[arg-type]


def _make_nano_banana2_client(timeout_s: int) -> Any:
    """genai client with a real client-side timeout (HttpOptions.timeout is in ms) — HL-2630."""
    from google import genai as gai
    from google.genai import types as genai_types
    return gai.Client(http_options=genai_types.HttpOptions(
        api_version="v1alpha",
        timeout=timeout_s * 1000,
    ))


async def _call_nano_banana2_edit(
    client: Any, image_bytes: bytes, mime_type: str, edit_instruction: str, timeout_s: int,
) -> tuple[bytes, str] | None:
    """One NanoBanana2 request. Returns (bytes, mime) of the first inline image, or None.

    No image_config.aspect_ratio: the aspect ratio is driven by the input image and the
    Edit_Instruction (Req 6.11). Test injection point (monkeypatch this module attribute)."""
    from google.genai import types as genai_types

    contents = [
        genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        genai_types.Part.from_text(text=edit_instruction),
    ]
    # HL-2630: wait_for backs up the HTTP timeout; AFC disabled so the SDK makes exactly
    # one request instead of looping up to 10 remote calls (observed 27-min hang).
    response = await asyncio.wait_for(
        asyncio.to_thread(
            client.models.generate_content,
            model=NANO_BANANA2_MODEL,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(disable=True),
            ),
        ),
        timeout=timeout_s + 15,
    )
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return None
    content = getattr(candidates[0], "content", None)
    for part in (getattr(content, "parts", None) or []):
        inline = getattr(part, "inline_data", None)
        if inline and getattr(inline, "data", None):
            return inline.data, (inline.mime_type or "image/png")
    return None


async def edit_image_variations(
    base_image_bytes: bytes,
    base_mime_type: str,
    edit_instruction: str,
    n_variations: int,
    *,
    task_id: str = "-",
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> list[dict[str, Any]]:
    """Generate up to `n_variations` edits of the base image with NanoBanana2 (Req 7).

    Returns:
        List sorted by `index` (1-based, request position) of Edited_Variation
        {"index": int, "image_b64": str, "mime_type": str}. Failed variations are
        omitted; the list may be empty. Never raises because a variation failed.
    Raises:
        ValueError if n_variations is not in 1..10 or the base image is empty.
    """
    if (isinstance(n_variations, bool) or not isinstance(n_variations, int)
            or not _EDIT_MIN_VARIATIONS <= n_variations <= _EDIT_MAX_VARIATIONS):
        raise ValueError(f"n_variations must be an int in [{_EDIT_MIN_VARIATIONS}, {_EDIT_MAX_VARIATIONS}]")
    if not base_image_bytes:
        raise ValueError("base_image_bytes must not be empty")

    timeout_s = max(10, getattr(settings, "IMAGE_GEN_TIMEOUT_SECONDS", 120))  # Req 7.6
    try:
        client = _make_nano_banana2_client(timeout_s)
    except Exception as exc:
        # Every request would fail anyway; let each variation fail (no raise) so the
        # pipeline turns the empty list into ImageEditingFailedError and Celery retries.
        logger.warning(f"[{task_id}] NanoBanana2 client init failed: {type(exc).__name__}")
        client = None

    logger.info(
        f"[{task_id}] NanoBanana2 edit start n={n_variations} "
        f"base_mime={base_mime_type} base_bytes={len(base_image_bytes)}"
    )

    async def _one(index: int) -> dict[str, Any] | None:
        max_attempts = 1 + len(_EDIT_RATE_LIMIT_BACKOFF_S)
        for attempt in range(1, max_attempts + 1):
            rate_limited = False
            # Semaphore per attempt, released before the backoff sleep so waits don't
            # hold a slot (Req 7.3: at most IMAGE_GEN_MAX_CONCURRENCY in flight).
            async with _image_semaphore():
                try:
                    result = await _call_nano_banana2_edit(
                        client, base_image_bytes, base_mime_type, edit_instruction, timeout_s,
                    )
                except Exception as exc:
                    if _is_image_rate_limit_error(exc):
                        rate_limited = True
                    else:
                        logger.warning(f"[{task_id}] NanoBanana2 edit v{index} failed: {type(exc).__name__}")
                        return None
                else:
                    if not result:
                        logger.warning(f"[{task_id}] NanoBanana2 edit v{index} failed: NoImageInResponse")
                        return None
                    data, mime = result
                    if not data or not isinstance(mime, str) or not mime.startswith("image/"):
                        logger.warning(
                            f"[{task_id}] NanoBanana2 edit v{index} failed: NoImageInResponse mime={mime}"
                        )
                        return None
                    logger.info(f"[{task_id}] NanoBanana2 edit v{index} OK mime={mime} bytes={len(data)}")
                    return {"index": index, "image_b64": base64.b64encode(data).decode(), "mime_type": mime}
            if rate_limited:
                if attempt >= max_attempts:
                    logger.warning(
                        f"[{task_id}] NanoBanana2 edit v{index} failed: RateLimit after {attempt} attempts"
                    )
                    return None
                delay = _EDIT_RATE_LIMIT_BACKOFF_S[attempt - 1]
                logger.warning(
                    f"[{task_id}] NanoBanana2 edit v{index} rate limited "
                    f"(attempt {attempt}/{max_attempts}) — backing off {delay}s"
                )
                await sleep(delay)
        return None

    results = await asyncio.gather(
        *[_one(i) for i in range(1, n_variations + 1)],
        return_exceptions=True,
    )
    variations: list[dict[str, Any]] = []
    for i, res in enumerate(results, start=1):
        if isinstance(res, BaseException):
            logger.warning(f"[{task_id}] NanoBanana2 edit v{i} failed: {type(res).__name__}")
        elif res:
            variations.append(res)
    variations.sort(key=lambda v: v["index"])
    logger.info(f"[{task_id}] NanoBanana2 edit done ok={len(variations)}/{n_variations}")
    return variations


# ---------------------------------------------------------------------------
# NanoBanana ADK Agent
# ---------------------------------------------------------------------------

_FALLBACK_INSTRUCTION = """\
You are the Image Generator (NanoBanana) for Fury's pipeline.

You only execute AFTER the Validador has approved the proposals.

Use generate_images_from_prompts with the complete list of image_prompts from the
ImagePrompter agent.

Return the generated_images list with plan_id and image_url for each item.
If any image fails to generate, flag it but do not halt — the TemplateMapper
can skip that entry or use a placeholder.
"""


def make_nano_banana_agent() -> Agent:
    """Lazy factory — creates a fresh Agent with current Langfuse config."""
    cfg = get_agent_config_from_langfuse(
        "fury.nano_banana",
        _FALLBACK_INSTRUCTION,
        cache_ttl_seconds=settings.LANGFUSE_CACHE_TTL_SECONDS,
    )
    return Agent(
        model=cfg["model"],
        name="nano_banana_agent",
        description=(
            "NanoBanana. Image generator. Only runs after Validador approves. "
            "Receives image_prompts and generates real images via the configured "
            "image API (DALL-E 3 / Imagen 3). Returns image_urls for each plan."
        ),
        instruction=cfg["instruction"],
        tools=[generate_images_from_prompts],
        # before_model_callback=safety_guard_before_model,
        # after_model_callback=safety_guard_after_model,
    )
